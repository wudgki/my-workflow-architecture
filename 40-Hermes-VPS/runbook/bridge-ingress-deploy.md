# bridge-ingress VPS 部署 Runbook

本文档记录如何在 VPS 上构建并运行 bridge-ingress（Telegram MTProto
listener），使其 7x24 监听指定群组消息并落盘到 `/data/inbox/Telegram-Captures/`。

> ⚠️ **本 runbook 只部署 bridge-ingress 单容器。**
> 不启动 intel-pipelines / watchdog / 全量 compose up。

---

## 前置条件

- [ ] PR #18（Telegram MTProto listener）已合并到 main
- [ ] PR #13 Cloudflare Tunnel smoke test 已通过
- [ ] VPS 已安装 Docker Engine（24+）
- [ ] 已在本地完成 `generate_session.py`，拿到 `TG_SESSION_STRING`
- [ ] 已通过 `list_dialogs.py` 确认目标群 chat_id
- [ ] VPS 可访问 Telegram MTProto 服务器（端口 443 出站）

---

## 步骤 1：VPS 拉取最新蓝图

```bash
cd /opt/hermes-blueprint
git checkout main
git pull --ff-only
```

确认 `50-Intelligence/community-bridges/bridge-ingress/` 目录存在且含
`tg_listener.py`。

---

## 步骤 2：创建 .env

```bash
cd /opt/hermes-blueprint/50-Intelligence/community-bridges/bridge-ingress
cat > .env << 'EOF'
TG_API_ID=<你的api_id>
TG_API_HASH=<你的api_hash>
TG_SESSION_STRING=<你的session_string>
TG_MEME_CHAT_IDS=-1002948440512
TG_CONTRACT_CHAT_IDS=-1003150146675,-1003116474257,-1003151436192
INBOX_PATH=/data/inbox
KEYWORDS_PATH=/blueprint/50-Intelligence/pipelines/keywords.yaml
LOG_LEVEL=info
LISTEN_PORT=8080
EOF
```

**安全要求**：

- 用 `nano .env` 编辑，不要 `cat .env` 到终端（防历史泄露）
- `.env` 已在 `.gitignore`，永不入库
- 不把 session string 发给任何 agent / 贴到任何在线平台

---

## 步骤 3：构建镜像

```bash
cd /opt/hermes-blueprint/50-Intelligence/community-bridges/bridge-ingress
docker build -t bridge-ingress:v0.2.0 .
```

预期：

- 构建成功，无报错
- 镜像大小 < 100 MB：`docker images bridge-ingress:v0.2.0`

---

## 步骤 4：准备数据目录和 keywords 挂载

```bash
# 创建 inbox 目录（bridge 写入目标）
sudo mkdir -p /data/inbox/Telegram-Captures

# keywords.yaml 已在蓝图仓里，直接挂载
ls /opt/hermes-blueprint/50-Intelligence/pipelines/keywords.yaml
```

---

## 步骤 5：启动容器

```bash
docker run -d \
  --name hermes-bridge-ingress \
  --restart on-failure:5 \
  --env-file /opt/hermes-blueprint/50-Intelligence/community-bridges/bridge-ingress/.env \
  -v /data/inbox:/data/inbox \
  -v /opt/hermes-blueprint/50-Intelligence/pipelines/keywords.yaml:/blueprint/50-Intelligence/pipelines/keywords.yaml:ro \
  -p 127.0.0.1:8080:8080 \
  bridge-ingress:v0.2.0
```

**说明**：

- `-p 127.0.0.1:8080:8080`：healthcheck 只绑 localhost，不暴露公网
- `--restart on-failure:5`：崩溃自动重试，最多 5 次
- keywords.yaml 以 `:ro` 只读挂载

---

## 步骤 6：验证启动

### 6.1 检查容器状态

```bash
docker ps -f name=hermes-bridge-ingress
```

期望：STATUS 为 `Up X seconds`。

### 6.2 检查日志

```bash
docker logs hermes-bridge-ingress 2>&1 | head -20
```

期望看到：

```json
{"ts":"...","level":"info","logger":"tg-listener","msg":"tg_listener_starting",...}
{"ts":"...","level":"info","logger":"tg-listener","msg":"tg_listener_connected",...}
```

**不应看到**：

- `tg_listener_not_authorized`（session 过期）
- `RuntimeError`（配置错误）
- 任何 secret / session string 明文

### 6.3 检查 /healthz

```bash
curl -s http://127.0.0.1:8080/healthz | python3 -m json.tool
```

期望：

```json
{
    "status": "ok",
    "listener_connected": true,
    "messages_processed": 0
}
```

`listener_connected: true` 表示 MTProto 连接成功。
`messages_processed` 会随着监听群有新消息逐渐增长。

---

## 步骤 7：验证消息落盘

等待监听群中有人发消息（或你用另一个账号在群里发一条测试消息），然后：

```bash
ls /data/inbox/Telegram-Captures/
```

期望出现新的 `.md` 文件：

```
2026-05-20_telegram_-1002948440512_12345.md
```

检查文件内容：

```bash
head -20 /data/inbox/Telegram-Captures/*.md | head -30
```

期望 front-matter 含：

- `source: telegram`
- `chat_id:` 对应你的监听群
- `message_id:` 消息 ID
- `phase:` phase_1..phase_4 或 null
- `watch_category:` meme 或 contract

---

## 步骤 8：持续运行确认

启动 30 分钟后再次检查：

```bash
curl -s http://127.0.0.1:8080/healthz
docker logs --tail 5 hermes-bridge-ingress
ls /data/inbox/Telegram-Captures/ | wc -l
```

确认：

- `listener_connected` 仍为 `true`
- `messages_processed` > 0（如果群里有消息）
- 没有 panic / restart

---

## 故障排查

| 现象 | 可能原因 | 处置 |
|---|---|---|
| 容器立即退出 | `.env` 缺少必填变量 | `docker logs hermes-bridge-ingress` 看 RuntimeError |
| `listener_connected: false` | session 过期 / 网络不通 | 在本地重新 `generate_session.py`；检查 VPS 出站 443 |
| `tg_listener_not_authorized` | session string 无效 | 重新生成 session，更新 .env，重启容器 |
| 容器正常但无文件产出 | 群里没有新消息 / chat_id 填错 | 在目标群发一条测试消息；核对 `list_dialogs.py` 输出 |
| 文件产出但 `phase: null` | 消息文本不匹配任何关键词 | 正常现象；或更新 keywords.yaml 加入相关关键词 |
| OOM killed | 群消息太多 / 内存不足 | `docker stats` 检查；加 `--memory=256m` 限制 |
| `Connection reset` 日志 | VPS 防火墙 / ISP 限制 Telegram | 检查出站 443；考虑通过 proxy 连接 |

---

## 停止 / 重启 / 清理

```bash
# 停止
docker stop hermes-bridge-ingress

# 重启（保留容器）
docker restart hermes-bridge-ingress

# 删除容器（数据在 /data/inbox 不受影响）
docker rm -f hermes-bridge-ingress

# 删除镜像（重新构建时需要）
docker rmi bridge-ingress:v0.2.0
```

---

## 明确禁止事项

- ❌ 执行全量 `docker compose up -d`
- ❌ 启动 intel-pipelines（尚未实现）
- ❌ 启动 watchdog（尚未实现）
- ❌ 把 `.env` 提交到 git
- ❌ 把 session string / api_hash 贴到任何在线平台
- ❌ 在 bridge 容器内执行任何写消息 / 改群设置操作
- ❌ 把容器日志贴到 PR / Issue / 公开 chat

---

## 验收记录

| 日期 | VPS | 构建 | /healthz | listener_connected | 首条消息落盘 | 备注 |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | _ | OK/FAIL | 200/FAIL | true/false | OK/FAIL | _ |

---

## 下一步（不在本 runbook 范围）

1. Watchdog 容器：监控 bridge 健康状态，挂了发 Telegram 告警
2. intel-pipelines：聚合 Telegram-Captures 生成 Daily Digest
3. Syncthing / rclone：把 VPS `/data/inbox/` 同步到主电脑
4. Compose 模板对齐：更新 `docker-compose.example.yml` 为 v0.2.0 变量

---

<!--
维护说明：
- 本文件只记录 bridge-ingress 单容器的部署 SOP
- 不要在本文件记录 watchdog / intel-pipelines / compose 全栈部署
- 如果 bridge 架构变化（加 Discord / 换 Telethon 版本），更新本文件
-->
