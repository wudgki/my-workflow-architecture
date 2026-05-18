# Runbook · Hermes 从 VPS 迁回本地副电脑

> 适用场景：VPS 资源不够 / 成本过高 / 想用本地 GPU / 长期跑大模型；需要把 Hermes 服务从 VPS 平滑迁到 **副电脑 (secondary)**。
> 风险等级：中。预计停机时间：30-60 分钟（如做并行灰度可 ≈ 0）。

---

## 一、前置检查清单

执行迁移前必须全部通过：

- [ ] 副电脑硬件：≥ 16 GB RAM / ≥ 200 GB SSD 可用 / 稳定有线网络
- [ ] 副电脑装好：Docker Desktop（或 Docker Engine + WSL2）/ Git / SSH
- [ ] 副电脑公网可达性方案确定（三选一）：
  - 内网穿透（frpc / Cloudflare Tunnel / Tailscale Funnel）
  - 仅局域网 + Tailscale 内网
  - 仅本地访问（不对外暴露）
- [ ] `90-Ops/secrets/hermes/` 已在副电脑落地（手动通过加密通道传输，**不走 Syncthing**）
- [ ] VPS 上 Hermes 当前版本号、镜像 tag 已记录到 `40-Hermes-VPS/runbook/_versions.md`
- [ ] 最近一次备份在 24 小时内，且 `90-Ops/backup/verify.sh` 校验通过
- [ ] 通知所有依赖 Hermes 的下游（Phase 2 / 3 / 4 项目、`50-Intelligence/`）

---

## 二、迁移策略选择

| 策略 | 适用 | 停机 | 复杂度 |
|---|---|---|---|
| **A · 冷迁** | 容忍停机 30-60 分钟 | 30-60 min | 低 |
| **B · 并行灰度** | 几乎零停机 | ≈ 0 | 中 |
| **C · 主备双活** | 后期长期保留 VPS 做热备 | 0 | 高 |

下文默认 **策略 A**（最简单），策略 B/C 在第八节给出差异。

---

## 三、迁移步骤（策略 A · 冷迁）

### 3.1 在 VPS 端冻结状态

```bash
# 1. 停止接收新任务（关闭 webhook 入口）
cd /opt/hermes
docker compose pause webhook-ingress

# 2. 等待队列排空
docker compose exec hermes-worker /app/scripts/drain-queue.sh

# 3. 停服
docker compose down
```

### 3.2 打包数据

```bash
# 数据卷 + 配置 + 索引
tar -czf hermes-snapshot-$(date +%Y%m%d-%H%M).tar.gz \
    /opt/hermes/data \
    /opt/hermes/config \
    /opt/hermes/index

# 校验
sha256sum hermes-snapshot-*.tar.gz | tee hermes-snapshot.sha256
```

### 3.3 传输到副电脑

```bash
# 在副电脑执行（推荐用 rsync over SSH）
rsync -avzP --partial \
    user@vps:/opt/hermes/hermes-snapshot-*.tar.gz \
    D:/AI-Workspace/40-Hermes-VPS/_migration-staging/

# 校验
sha256sum -c hermes-snapshot.sha256
```

### 3.4 在副电脑还原

```bash
# 解压到目标目录（不直接覆盖 D:\AI-Workspace\40-Hermes-VPS\，那里只是配置）
mkdir -p D:/HermesData
tar -xzf hermes-snapshot-*.tar.gz -C D:/HermesData/

# 起服（用 40-Hermes-VPS/deploy/docker-compose.local.yml）
cd D:/AI-Workspace/40-Hermes-VPS/deploy
docker compose -f docker-compose.local.yml up -d
```

### 3.5 切流量

| 公网方案 | 操作 |
|---|---|
| Cloudflare Tunnel | 把原 hostname 的 tunnel 指向副电脑的 cloudflared |
| frp | 改 frps 配置，指向副电脑 frpc |
| Tailscale | 通知下游改用副电脑的 magic dns 名 |

```bash
# 健康检查
curl https://hermes.<your-domain>/health
# 期望：{"status":"ok","version":"<x.y.z>","host":"samuel-secondary"}
```

### 3.6 关停 VPS Hermes

确认副电脑稳定运行 **24 小时** 后再做：

```bash
# VPS 上
cd /opt/hermes
docker compose down
docker volume prune     # 谨慎
# 仅保留镜像 + 一份 snapshot 在 VPS 留 7 天作为回退
```

---

## 四、回滚预案

如果副电脑跑不起来 / 性能不达标：

```bash
# VPS 端（如还在 7 天保留期内）
cd /opt/hermes
docker compose up -d
# 流量切回 VPS
```

副电脑端：

```bash
docker compose -f docker-compose.local.yml down
# 数据保留在 D:\HermesData\，下次再试
```

---

## 五、迁移后的目录变化

| 路径 | 迁移前 | 迁移后 |
|---|---|---|
| 配置源 | `40-Hermes-VPS/services/*` (VPS 拉取) | `40-Hermes-VPS/services/*` (副电脑拉取) |
| 部署 yaml | `40-Hermes-VPS/deploy/docker-compose.vps.yml` | `40-Hermes-VPS/deploy/docker-compose.local.yml` |
| 真实数据 | VPS `/opt/hermes/data` | 副电脑 `D:/HermesData/` |
| 密钥 | VPS `/opt/hermes/secrets` | 副电脑 `90-Ops/secrets/hermes/` |
| 公网入口 | VPS 的 80/443 | Cloudflare Tunnel / Tailscale Funnel |

---

## 六、网络与可用性新风险

迁回本地后**新增**的风险点：

1. **家庭宽带不稳定** → 用 Cloudflare Tunnel 屏蔽公网 IP 变化；对外不暴露端口。
2. **副电脑断电 / 重启** → systemd / 任务计划程序设置开机自启；UPS 可选。
3. **NAT 穿透延迟** → 关键 webhook 加重试 + 队列。
4. **本地杀软干扰 Docker 网络** → Windows Defender / 杀软白名单。
5. **同步与服务争抢磁盘** → Hermes 数据目录 **不要** 放在 Syncthing 同步范围内（已通过 `D:/HermesData` 隔离）。

---

## 七、验收清单

迁移完成后逐项确认：

- [ ] `https://hermes.<domain>/health` 返回 `host: samuel-secondary`
- [ ] `50-Intelligence/community-bridges/*` webhook 调用成功率 ≥ 99%（观察 24h）
- [ ] Wiki 索引能命中近 7 天新增笔记
- [ ] Phase 2 / 3 / 4 项目能正常调用 Hermes 接口
- [ ] 飞书 / Telegram 告警正常发出
- [ ] 副电脑 CPU / 内存 / 磁盘占用稳态在阈值内（CPU < 60%、内存 < 70%）
- [ ] `90-Ops/backup/` 第一份本地版 Hermes 数据备份生成

---

## 八、策略 B / C 的关键差异

### B · 并行灰度

- 不停 VPS Hermes，副电脑同时起一份，使用**只读镜像数据**先跑。
- 通过 webhook 入口的"分流配置"把 1% / 10% / 50% / 100% 流量逐步切到副电脑。
- 全量切流后再按 3.6 关停 VPS。
- 适用于已建立"分流网关"（Cloudflare Worker / nginx）的场景。

### C · 主备双活

- 长期保留 VPS Hermes 作为**热备**：每日自副电脑同步快照到 VPS。
- DNS 用 failover（Cloudflare Load Balancer / 健康检查 + 切换）。
- 成本最高，复杂度最高，仅在 Phase 3 / 4 大规模上线后考虑。

---

## 九、待补全（TODO）

- [ ] `40-Hermes-VPS/deploy/docker-compose.local.yml` 模板
- [ ] `40-Hermes-VPS/runbook/_versions.md`：Hermes 版本变更记录
- [ ] `_migration-staging/.gitkeep`：迁移暂存目录占位
- [ ] 一次实战演练后回写本文件的"实际耗时"和"踩坑记录"小节
