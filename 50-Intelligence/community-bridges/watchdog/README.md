# watchdog (v0.1.0)

Hermes 第二个业务容器：监控 bridge-ingress 健康状态，挂了通过独立
Telegram bot 告警到你的私聊。

> ⚠️ 本服务**只读 + 只发告警**。
> 不接触 bridge 的 inbox，不发监听群消息，不修改任何数据。

---

## 架构

```
                   每 60s
bridge-ingress  <----------  watchdog
   /healthz        (curl)        |
                                 | 状态变化时
                                 v
                       Telegram Bot API
                       (api.telegram.org)
                                 |
                                 v
                          你的私聊
                       (告警 bot 推送)
```

---

## 状态机

| 当前状态 | 检查结果 | 新状态 | 动作 |
|---|---|---|---|
| unknown | OK | healthy | 仅 info 日志 |
| unknown | FAIL | unknown* | 失败计数 +1 |
| healthy | OK | healthy | 重置失败计数 |
| healthy | FAIL | unknown* | 失败计数 +1，达到阈值 → unhealthy |
| healthy | FAIL × N | unhealthy | **发告警** |
| unhealthy | OK | healthy | **发恢复告警**（含 downtime） |
| unhealthy | FAIL | unhealthy | 不重复告警（防 spam） |

\* 计数到达 `FAILURE_THRESHOLD` 之前是中间态，不告警。

---

## 失败判定

任意一个条件触发失败计数：

1. HTTP 请求超时或连接拒绝（容器死了）
2. HTTP 状态码非 200
3. JSON 解析失败
4. `listener_connected: false`（Telegram 连接断了）

---

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `ALERT_TELEGRAM_BOT_TOKEN` | ✅ | — | BotFather 给的 token（专用告警 bot） |
| `ALERT_TELEGRAM_CHAT_ID` | ✅ | — | 你的私聊 ID（数字） |
| `BRIDGE_HEALTHZ_URL` | | `http://bridge-ingress:8080/healthz` | bridge 的 healthz 地址 |
| `CHECK_INTERVAL_SECONDS` | | `60` | 轮询间隔秒数 |
| `FAILURE_THRESHOLD` | | `3` | 连续失败几次算 unhealthy（含此次） |
| `LOG_LEVEL` | | `info` | `info` / `debug` |

> ⚠️ **告警 bot token = 完整控制权**。
> 只存在 VPS 本地 `.env`，永不入 git，永不发给 agent。

---

## 告警示例

**Unhealthy（首次）**：

```
[Hermes VPS] bridge-ingress UNHEALTHY
time: 2026-05-20 03:14:15 UTC
reason: listener_disconnected
last_error: connection timeout to 91.108.56.150:443
action: SSH to VPS, check 'docker logs hermes-bridge-ingress'
```

**Recovered**：

```
[Hermes VPS] bridge-ingress RECOVERED
time: 2026-05-20 03:24:15 UTC
downtime: 10 minutes
```

---

## 不告警的情况（避免噪音）

- 容器刚启动，state = unknown 直到第一次成功检查
- 失败次数 < `FAILURE_THRESHOLD`（短暂网络抖动）
- 已在 unhealthy 状态时再次失败（不重复告警）
- bridge 重启过程中（healthcheck 暂时不通，几秒内恢复）

---

## 安全

- `ALERT_BOT_TOKEN` 永不打印到日志、stdout、stderr
- 告警消息正文不含监听群 chat_id、不含监听账号 session
- 容器以非 root 用户 `watchdog` 运行
- 容器无文件写权限（只调 stdout 日志和 outbound HTTPS）
- 没有挂载 docker.sock，没有特权模式

---

## 不做（明确边界）

- 不监控 bridge 之外的服务（cloudflared / 主机系统等留给后续 PR）
- 不持久化失败历史（重启状态归零）
- 不做 escalation（重复告警 / 多渠道 / on-call 轮值）
- 不重启 bridge（你收到告警后人工处理）
- 不接 PagerDuty / OpsGenie / 邮件
- 不接 Discord / 飞书

---

## 本地开发

```bash
# 语法检查
bash -n watchdog.sh
bash -n alert.sh

# 跑单元测试
bash tests/test_logic.sh
bash tests/test_alert.sh

# 镜像构建
docker build -t hermes-watchdog:dev .
docker images hermes-watchdog:dev   # 期望 < 20 MB
```

---

## 部署

完整 SOP 见 `90-Ops/runbook/watchdog-deploy.md`。
