# 40-Hermes-VPS/deploy/ · 部署模板与首次上线 SOP

本目录存放 Hermes 服务在 VPS 上的部署蓝图。**模板先行，代码后到** —— 在 `50-Intelligence/community-bridges/` 的代码写好之前，本目录提供完整的服务编排，让 VPS 一旦准备好就能 `docker compose up`。

---

## 文件清单

| 文件 | 用途 |
|---|---|
| `docker-compose.example.yml` | 4 个服务的编排模板。**故意命名 `.example.yml`** 防止被默认 `docker compose up` 误启动 |
| `README.md` | 本文件（中文部署 SOP） |

环境变量模板在 `../env/.env.example`。

---

## 服务架构（一张图）

```
                Internet
                   |
                   |  HTTPS (only)
                   v
            +---------------+
            |  cloudflared  |   <-- 不开任何 VPS 端口
            +-------+-------+
                    |
            +-------v---------+
            | bridge-ingress  |   :8080 (internal only)
            |  Discord/TG/    |   写入 /data/inbox
            |  Feishu webhook |
            +-------+---------+
                    |
                    v (internal volume)
            +-----------------+
            | intel-pipelines |   每小时一次或定时
            | (cron-like)     |   读 keywords.yaml
            |                 |   产生 daily digest
            +-----------------+
                    |
                    | (健康检查)
                    v
            +---------------+
            |   watchdog    |   每 60s 巡检
            |   告警 -> TG  |   + 磁盘水位
            +---------------+
```

**关键设计**：

- 公网入口只走 Cloudflare Tunnel —— **VPS 防火墙保持只开 22**
- 服务之间走 docker 内网，外部不可达
- `blueprint-ro` 把蓝图仓库以**只读**方式挂进容器，让 intel-pipelines 能读 `keywords.yaml` 但**绝对不能改**
- watchdog 用 read-only docker.sock，能查询容器状态但不能管理容器

---

## 首次部署 SOP

### 0. 前置准备

- [ ] VPS 装好 Docker Engine + Docker Compose plugin（不是 docker-compose v1）
- [ ] VPS 防火墙只开 22（SSH）。Cloudflare Tunnel 主动连出，不需要入口端口
- [ ] 已申请好 Cloudflare 免费账户，创建一个 Tunnel 并拿到 connector token
- [ ] 已创建 Discord bot / Telegram bot 并拿到 token

### 1. 在 VPS 上 clone 蓝图仓库

```bash
sudo mkdir -p /opt/hermes
sudo chown $(id -u):$(id -g) /opt/hermes
cd /opt/hermes
git clone https://github.com/wudgki/my-workflow-architecture.git blueprint
```

### 2. 准备工作目录

```bash
cd /opt/hermes/blueprint/40-Hermes-VPS/deploy
cp docker-compose.example.yml docker-compose.yml

cd ../env
cp .env.example .env
chmod 600 .env
nano .env   # 填入真实值，每个 REPLACE_ME 都要换掉
```

### 3. 拉镜像（首次部署时镜像还不存在）

⚠️ 当前 `BRIDGE_IMAGE_TAG`、`INTEL_IMAGE_TAG`、`WATCHDOG_IMAGE_TAG` 都是 `v0.0.0-placeholder`。这些镜像目前**不存在** —— 等 `50-Intelligence/community-bridges/` 的代码写好并发布到 GHCR 之后再回来填真实 tag。

在那之前你可以：

- **只启动 cloudflared** 验证 tunnel 通路：
  ```bash
  cd /opt/hermes/blueprint/40-Hermes-VPS/deploy
  docker compose --env-file ../env/.env up -d cloudflared
  docker compose logs -f cloudflared
  ```
- 看到 `Connection ... registered` 字样即成功

### 4. 全量启动（镜像就绪后）

```bash
cd /opt/hermes/blueprint/40-Hermes-VPS/deploy
docker compose --env-file ../env/.env up -d
docker compose ps
```

期望所有服务 `running` 且 `healthy`。

### 5. 验证

```bash
# 容器健康
docker compose ps

# 查日志
docker compose logs --tail=50 bridge-ingress
docker compose logs --tail=50 intel-pipelines
docker compose logs --tail=50 watchdog

# 触发一个测试 webhook（需要替换为你 cloudflare tunnel 暴露的域名）
curl -X POST https://hermes.<your-domain>/discord/test \
     -H 'Content-Type: application/json' \
     -d '{"event":"smoke-test"}'

# 验证 capture 落到 /data/inbox
docker compose exec bridge-ingress ls -la /data/inbox
```

### 6. 停服 / 重启 / 升级

```bash
# 平滑停服
docker compose down

# 拉新镜像并重启
docker compose pull
docker compose up -d

# 紧急停所有
docker compose kill
```

---

## 与本地 / 副电脑的关系

| 通道 | 方向 | 用途 |
|---|---|---|
| Git pull | VPS ← GitHub | 获取最新蓝图（compose 文件 / keywords / agent 定义） |
| SSH rsync | 副电脑 ← VPS | 把 `/data/inbox` 拉回主机做 Wiki 处理（不走 Syncthing） |
| Cloudflare Tunnel | Internet → VPS | 接收 Discord/Telegram/飞书 webhook |
| 告警 webhook | VPS → Telegram/飞书 | watchdog 主动推送 |

VPS **不参与 Syncthing**。这点在 `90-Ops/sync/syncthing-folders.yaml` 的 `never_share` 里已经声明。

---

## 资源占用预估

按当前模板的 `deploy.resources.limits`：

| 服务 | 内存上限 | CPU 上限 |
|---|---|---|
| bridge-ingress | 512M | 0.5 core |
| intel-pipelines | 768M | 1.0 core |
| watchdog | 128M | 0.1 core |
| cloudflared | 128M | 0.2 core |
| **合计** | **~1.5G** | **~1.8 core** |

**最低 VPS 配置**：2 vCPU / 2 GB RAM / 20 GB SSD（足够，留一半余量给 OS）。
**推荐 VPS 配置**：2 vCPU / 4 GB RAM / 40 GB SSD。

---

## 安全边界

- ❌ **不要**把 `.env` 提交到 git（`.gitignore` 已经覆盖）
- ❌ **不要**在 compose 里硬编码任何 token / API key —— 全部通过 `${VAR}` 引用 .env
- ❌ **不要**给 docker.sock 挂 read-write —— watchdog 只用 `:ro`
- ❌ **不要**直接在 VPS 上 `vim` 编辑业务策略 —— 业务策略归 `30-Phases/`，VPS 只负责执行
- ✅ Cloudflare Tunnel 是唯一公网入口，关掉 tunnel 就能瞬间断网隔离
- ✅ 所有镜像 tag **必须固定版本**，禁用 `:latest`

---

## 后续 PR 路线

本 PR 只提供模板。落地依赖：

1. **PR：community-bridges 代码 + 镜像发布** → 把 `BRIDGE_IMAGE_TAG` 从 `v0.0.0-placeholder` 改为真实版本
2. **PR：intel-pipelines 代码 + 镜像发布** → 同上
3. **PR：watchdog 代码 + 镜像发布** → 同上（最简单，可以先做这个）
4. **PR：实战部署后回写本 README** → 把第 5 步"验证"的真实日志贴进来作为 reference
