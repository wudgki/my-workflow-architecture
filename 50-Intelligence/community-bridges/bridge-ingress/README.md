# bridge-ingress (PR #15, Telegram-only MVP)

Hermes 第一台业务容器：接收社区桥的 webhook，标准化为 Markdown +
front-matter，写入 `/data/inbox/Telegram-Captures/`，供下游
`intel-pipelines` 与 `wiki-writer` agent 消费。

> 本 PR 只实现 **Telegram** 一条线，Discord / Feishu 留给后续 PR。
> 接口契约见 `../SPEC-bridge-ingress.md`（PR #14 已合并）。

---

## 端点

| 方法 | 路径 | 用途 | 鉴权 |
|---|---|---|---|
| `GET` | `/healthz` | 健康检查（docker compose / 手工 curl） | 无 |
| `POST` | `/webhook/telegram` | Telegram bot webhook 接收 | `X-Telegram-Bot-Api-Secret-Token` 头 |

未实现端点（**故意不留占位**）：`/webhook/discord`、`/webhook/feishu`。

---

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `TELEGRAM_WEBHOOK_SECRET` | ✅ | — | 与 Telegram `setWebhook` 的 `secret_token` 完全一致；常量时间比对 |
| `INBOX_PATH` | | `/data/inbox` | 落盘根目录；写入 `<INBOX_PATH>/Telegram-Captures/` |
| `KEYWORDS_PATH` | | `/blueprint/50-Intelligence/pipelines/keywords.yaml` | Phase 路由词典（**只读**挂载） |
| `LOG_LEVEL` | | `info` | `debug` / `info` / `warning` / `error` |
| `LISTEN_PORT` | | `8080` | 容器内监听端口 |
| `TELEGRAM_BOT_TOKEN` | | — | v1 不依赖；预留给将来主动调用 Telegram API（如 setWebhook 自检）|

> ⚠️ **绝不**把真实 secret 写进任何被 git 跟踪的文件（compose / README /
> 测试 fixture / 注释）。`tests/` 与 `smoke-test.sh` 全部使用
> `fake-secret-*` 字面量。

---

## 文件名格式（有意偏离 Inbox-Processing-Rules）

落盘文件名是：

```
YYYY-MM-DD_telegram_<chat_id>_<message_id>.md      (UTC 日期)
```

**这是有意为之的偏离**，不是 bug：

1. **幂等防重投**：Telegram 在 webhook 返回非 2xx 或超时时会重投，
   同一对 `(chat_id, message_id)` 必须落在同一路径，让重投只是覆盖
   相同字节，不产生重复文件。
2. **不依赖 LLM**：Inbox-Processing-Rules 的"主题 slug"形式需要语义
   理解，bridge-ingress 不在热路径上调任何上游 / 模型。
3. **后续重命名由 wiki-writer 负责**：`20-Claude-Code/agents/wiki-writer.md`
   在把 capture 升级进 Wiki 时改为可读名。下游消费者**不要**把这个
   文件名当人读名，应当读 front-matter 里的 `phase` / `source_id` 字段。

---

## front-matter 字段

```yaml
captured_at: 2026-05-20T03:14:15+00:00       # 本桥落盘时间 (UTC)
source: telegram
source_id: telegram:<chat_id>:<message_id>
chat_id: -100199988877
message_id: 4242
message_date: 2024-05-06T12:53:20+00:00      # Telegram message.date (UTC)
from_username: alice                          # 可空
phase: 3                                      # 1/2/3/4 或 null
tags: []
status: raw                                   # 下游可改成 processed / promoted
priority: p2
owner: intel-summarizer
bridge_version: 0.1.0
```

`phase` 来自 `phase_router.py` 对 `text || caption` 的匹配：
case-insensitive substring，`phase_1 → phase_4` first-match-wins，
命中 `global_exclude` 强制 `null`。

---

## 本地构建与验证

完整自动化在 `tests/smoke-test.sh`，人读流程在
`90-Ops/runbook/telegram-bridge-smoke-test.md`。

简版：

```bash
# 在本目录
docker build -t bridge-ingress:dev .
pytest -q     # 需先 pip install -r requirements.txt + pytest httpx
```

预期：

- 镜像 < 100 MB
- pytest 全部 PASS
- `tests/smoke-test.sh` 在装了 docker 的机器上一键全绿

---

## 不做（明确边界）

- 不发布到 GHCR（先本地 `bridge-ingress:dev`）
- 不接 Discord / Feishu webhook
- 不持久化已读集合（幂等靠文件名）
- 不主动调 Telegram API
- 不读 / 不写 `90-Ops/secrets/`
- 不在日志、注释、测试 fixture 里出现真实 token

---

## 与 SPEC-bridge-ingress.md 的对应

| SPEC 条款 | 落地位置 |
|---|---|
| §2.1 `/healthz` | `main.py::healthz` |
| §2.3 Telegram secret_token 验签 | `signature.py` |
| §3 Markdown + front-matter 格式 | `inbox_writer.py` |
| §4.1 Phase 路由 first-match-wins | `phase_router.py::route` |
| §4.2 keywords.yaml 热重载 | `phase_router.py::reload_if_changed`（每请求一次 stat，**不开后台线程**——这是 PR #15 与 SPEC 的实现差异，更简单且时效更高） |
| §5 结构化 JSON 日志 | `logger.py`（字段白名单防 secret 泄露） |
| §6 失败策略 | 401（鉴权失败）/ 400（JSON 错）/ 200+log（payload 不是 message） |
| §7 环境变量 | 见上表 |
