# Cloudflare Tunnel Smoke Test Runbook

本文档记录已验证通过的 VPS Cloudflare Tunnel 网络通路验收流程。

---

## 前置条件

- [ ] PR #12（docker-compose.example.yml 部署模板）已合并到 main
- [ ] VPS 已安装 Docker Engine + Docker Compose plugin
- [ ] 已在 [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/) 创建 Tunnel
- [ ] 已拿到 `CLOUDFLARE_TUNNEL_TOKEN`（长 base64 字符串）
- [ ] **Token 不得提交 GitHub，不得发给任何 agent，不得贴到 PR 或聊天窗口**

---

## 步骤 1：VPS 拉取蓝图

```bash
cd /opt
git clone https://github.com/wudgki/my-workflow-architecture.git hermes-blueprint
cd /opt/hermes-blueprint
git checkout main
git pull --ff-only
```

如果 PR #12 尚未合并到 main，也可临时切分支：

```bash
git fetch origin
git checkout -B feat/hermes-deploy-template origin/feat/hermes-deploy-template
```

---

## 步骤 2：创建 compose 和 env

```bash
cd /opt/hermes-blueprint/40-Hermes-VPS/deploy
cp docker-compose.example.yml docker-compose.yml
cp ../env/.env.example ../env/.env
nano ../env/.env
```

**重要**：

- `.env` 必须基于 `.env.example` 创建（包含所有变量的占位）
- 不要只写 `CLOUDFLARE_TUNNEL_TOKEN` 一行
- 除 `CLOUDFLARE_TUNNEL_TOKEN` 外，其它业务 token 在 smoke test 阶段可以保留 `REPLACE_ME`
- 不要 `cat ../env/.env`，避免终端历史泄露 token
- `.env` 已被 `.gitignore` 忽略，永不入库

---

## 步骤 3：验证配置

```bash
docker compose \
  --env-file ../env/.env \
  -f docker-compose.yml \
  config
```

期望：YAML 解析成功，输出渲染后的 compose 配置。业务 token 为 `REPLACE_ME` 时 compose config 会报变量未设置的 warning，但不影响 cloudflared 单独启动。

---

## 步骤 4：只启动 cloudflared

```bash
docker compose \
  --env-file ../env/.env \
  -f docker-compose.yml \
  up -d --no-deps cloudflared
```

**`--no-deps` 确保不会连带启动其它 placeholder 服务。**

---

## 步骤 5：查看日志

```bash
docker compose \
  --env-file ../env/.env \
  -f docker-compose.yml \
  logs -f cloudflared
```

### 成功标准

日志出现：

```text
Registered tunnel connection connIndex=0 connection=<id> ...
```

本次实测已确认出现多条 `Registered tunnel connection`，连接到多个 Cloudflare PoP（如 `hel01` / `fra08` / `fra03`），证明 VPS 到 Cloudflare 的网络通路已连通。

Token 在日志中以 `token:*****` 形式遮蔽，不会泄露。

---

## 步骤 6：非阻塞 warning 记录

```text
failed to sufficiently increase receive buffer size
```

**说明**：

- 这是 QUIC/UDP buffer 性能提示，不是错误
- 当前阶段只是 tunnel smoke test，不影响验收
- 后续真实生产流量阶段如果遇到性能问题再处理
- 如需修复：`sysctl -w net.core.rmem_max=2500000`（写入 `/etc/sysctl.conf` 持久化）

---

## 明确禁止事项

本 smoke test 阶段**严格禁止**：

- ❌ 执行全量 `docker compose up -d`
- ❌ 启动 `bridge-ingress`（placeholder 镜像不存在）
- ❌ 启动 `intel-pipelines`（placeholder 镜像不存在）
- ❌ 启动 `watchdog`（placeholder 镜像不存在 + docker.sock 高权限未评估）
- ❌ 测试 Docker socket 挂载
- ❌ 填入真实 Discord / Telegram / Feishu token（不需要，只验 tunnel）
- ❌ 提交 `.env` 到 git
- ❌ 把 token 发给 Kiro / Claude / ChatGPT 或贴到 PR

---

## 停止 smoke test

验证完成后停掉 cloudflared：

```bash
docker compose \
  --env-file ../env/.env \
  -f docker-compose.yml \
  stop cloudflared
```

如需完全清理（含网络和容器）：

```bash
docker compose \
  --env-file ../env/.env \
  -f docker-compose.yml \
  down
```

---

## 验收记录

| 日期 | VPS | Tunnel 连通 | PoP 节点 | Warning | 备注 |
|---|---|---|---|---|---|
| 2026-05-19 | 已验证 | 多条 Registered | hel01, fra08, fra03 | UDP buffer warning | 首次 smoke test 通过 |

---

## 下一步

Tunnel 网络通路已验证。后续动作（不在本 runbook 范围）：

1. 在 Cloudflare Dashboard 配置 Public Hostname → `localhost:8080`
2. 等 `bridge-ingress` 镜像发布后，启动 bridge + cloudflared 做端到端 webhook 测试
3. 逐步启动 intel-pipelines / watchdog

---

<!--
维护说明：
- 本文件只记录 Cloudflare Tunnel 的 smoke test SOP
- 后续如果 tunnel 配置变化（换域名/换 token/加 Access Policy），更新本文件
- 不要在本文件记录业务服务（bridge/intel/watchdog）的验证流程
-->
