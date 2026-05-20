# watchdog VPS 部署 Runbook

本文档记录如何在 VPS 上构建并运行 watchdog 容器，使其 7x24 监控
bridge-ingress 健康状态，并在挂掉或恢复时通过专用 Telegram bot
告警到你的私聊。

> ⚠️ **本 runbook 只部署 watchdog 单容器。**
> 不启动 intel-pipelines / 全量 compose up。
> 假设 bridge-ingress 已按 `bridge-ingress-deploy.md` 跑通。

---

## 前置条件

- [ ] PR #24（watchdog 容器）已合并到 main
- [ ] bridge-ingress 已在 VPS 上稳定运行（`/healthz` 能访问）
- [ ] 已通过 BotFather 创建专用告警 bot，拿到 `ALERT_TELEGRAM_BOT_TOKEN`
- [ ] 已通过 `@userinfobot` 拿到自己的私聊数字 ID（`ALERT_TELEGRAM_CHAT_ID`）
- [ ] **告警 bot 已与你私聊互动过一次**（在 Telegram 里给 bot 发 `/start`，否则 bot 无法主动给你发消息）
- [ ] VPS 可访问 `api.telegram.org:443` 出站

---

## 步骤 1：VPS 拉取最新蓝图

```bash
cd /opt/hermes-blueprint
git checkout main
git pull --ff-only
```

确认 `50-Intelligence/community-bridges/watchdog/` 目录存在。

---

## 步骤 2：创建 watchdog .env

```bash
cd /opt/hermes-blueprint/50-Intelligence/community-bridges/watchdog
nano .env
```

填入：

```env
ALERT_TELEGRAM_BOT_TOKEN=<你的告警bot token>
ALERT_TELEGRAM_CHAT_ID=<你的私聊数字id>
BRIDGE_HEALTHZ_URL=http://hermes-bridge-ingress:8080/healthz
CHECK_INTERVAL_SECONDS=60
FAILURE_THRESHOLD=3
LOG_LEVEL=info
```

**安全要求**：

- 用 `nano .env` 编辑，不要 `cat .env` 到终端
- `.env` 已被 `.gitignore` 忽略
- **告警 bot token 永不发给任何 agent / 贴到任何在线平台**
- 如果 token 泄露：去 BotFather 用 `/revoke` 立即作废

---

## 步骤 3：构建镜像

```bash
docker build -t hermes-watchdog:v0.1.0 .
docker images hermes-watchdog:v0.1.0
```

期望：构建成功，镜像 < 20 MB。

---

## 步骤 4：确保 bridge 与 watchdog 在同一 docker network

watchdog 需要能用容器名访问 bridge 的 `/healthz`。

```bash
# 检查现有 network
docker network ls | grep hermes

# 如果不存在 hermes-net，创建一个
docker network create hermes-net 2>/dev/null || true

# 把 bridge-ingress 加入网络（如果还没加）
docker network connect hermes-net hermes-bridge-ingress 2>/dev/null || true
```

---

## 步骤 5：启动 watchdog

```bash
docker run -d \
  --name hermes-watchdog \
  --restart on-failure:5 \
  --network hermes-net \
  --env-file /opt/hermes-blueprint/50-Intelligence/community-bridges/watchdog/.env \
  hermes-watchdog:v0.1.0
```

**说明**：

- `--network hermes-net`：让 watchdog 用 DNS 解析 `hermes-bridge-ingress`
- `--restart on-failure:5`：watchdog 自身崩溃也会自动重启
- 不暴露端口（watchdog 没有入站请求）
- 不挂载任何 volume（容器无持久化）

---

## 步骤 6：验证启动

### 6.1 检查容器状态

```bash
docker ps -f name=hermes-watchdog
```

期望：STATUS 为 `Up X seconds`。

### 6.2 检查日志

```bash
docker logs hermes-watchdog 2>&1 | head -10
```

期望看到：

```json
{"ts":"...","level":"info","logger":"watchdog","msg":"watchdog_starting version=0.1.0 url=http://hermes-bridge-ingress:8080/healthz"}
{"ts":"...","level":"info","logger":"watchdog","msg":"initial_state_healthy"}
```

**不应看到**：

- `missing_env`（环境变量没填）
- `missing_dep`（curl/jq 没装）
- 任何 token / chat id 明文

### 6.3 持续观察 5 分钟

```bash
docker logs -f hermes-watchdog
```

正常时只有 debug 级别的 `check_ok` 日志（默认 `LOG_LEVEL=info` 时不显示）。
如果想看到每次检查，临时改 `.env` 里 `LOG_LEVEL=debug` 然后重启容器。

---

## 步骤 7：触发告警测试

### 测试 unhealthy 告警

故意停掉 bridge-ingress：

```bash
docker stop hermes-bridge-ingress
```

等待 `FAILURE_THRESHOLD * CHECK_INTERVAL_SECONDS` 秒（默认 3 × 60 = 3 分钟）。

期望：

- 你的 Telegram 私聊收到告警 bot 的 UNHEALTHY 消息
- watchdog 日志出现 `state_transition_to_unhealthy`

### 测试 recovery 告警

重启 bridge-ingress：

```bash
docker start hermes-bridge-ingress
```

等待 `CHECK_INTERVAL_SECONDS` 秒（默认 60 秒）。

期望：

- 你的 Telegram 私聊收到告警 bot 的 RECOVERED 消息（含 downtime 分钟数）
- watchdog 日志出现 `state_transition unhealthy_to_healthy`

---

## 故障排查

| 现象 | 可能原因 | 处置 |
|---|---|---|
| 容器立即退出 | `.env` 缺少 `ALERT_TELEGRAM_BOT_TOKEN` 或 `ALERT_TELEGRAM_CHAT_ID` | `docker logs hermes-watchdog` 看 `missing_env` |
| `http_unreachable` 持续出现 | 不在同一 network / bridge 容器名不对 | `docker network inspect hermes-net` 确认两容器都连上 |
| `alert_send_failed http_code=400` | bot token 错或 chat id 错 | 重新核对；确认 bot 已 `/start` 过 |
| `alert_send_failed http_code=401` | token 已被 revoke | 去 BotFather 重新生成 |
| `alert_send_failed http_code=403` | bot 没和你私聊过 | 在 Telegram 里给 bot 发 `/start` |
| 收到第一条告警后再也不收 | 状态机正确：unhealthy 期间不重复告警 | 这是设计行为，不是 bug |
| 日志里看到 token 字符串 | **代码 bug** | 立即 revoke token，提 PR fix |

---

## 停止 / 重启 / 清理

```bash
docker stop hermes-watchdog
docker restart hermes-watchdog
docker rm -f hermes-watchdog
docker rmi hermes-watchdog:v0.1.0
```

watchdog 无持久化数据，可以随时重启不影响监控覆盖率（重启后状态机
从 `unknown` 开始，第一次成功检查会进入 `healthy`，不会误告警）。

---

## 明确禁止事项

- ❌ 把 `ALERT_TELEGRAM_BOT_TOKEN` 复制到聊天 / PR / commit / Issue
- ❌ 把告警 bot 加进任何监听群（它的作用域是 1 对 1 私聊）
- ❌ 启动 intel-pipelines / 全量 compose up
- ❌ 让 watchdog 自动重启 bridge（设计上人工介入，不做自愈）
- ❌ 把告警消息正文截图发到 PR / Issue（可能含 last_error 中的内部信息）

---

## 验收记录

| 日期 | VPS | 构建 | watchdog 启动 | bridge 停止后告警 | bridge 恢复后告警 | 备注 |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | _ | OK/FAIL | OK/FAIL | 收到/未收到 | 收到/未收到 | _ |

---

## 下一步（不在本 runbook 范围）

1. intel-pipelines：聚合 Telegram-Captures 生成 Daily Digest
2. Compose 模板对齐：把 watchdog 加进 docker-compose.example.yml
3. 多渠道告警：邮件 / 飞书 / Slack（视需要）
4. 监控范围扩展：cloudflared / 主机 disk / VPS 系统指标

---

<!--
维护说明：
- 本文件只记录 watchdog 单容器的部署 SOP
- 如果 watchdog 加新检查项（disk / memory / cloudflared），更新本文件
- 不在本文件记录 bridge / intel-pipelines 的部署细节
-->
