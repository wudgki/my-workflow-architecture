# bridge-ingress (v0.2.0, Telegram MTProto Listener)

Hermes 第一台业务容器：通过 Telegram MTProto 协议（Telethon userbot）
主动监听指定群组消息，标准化为 Markdown + front-matter，写入
`/data/inbox/Telegram-Captures/`，供下游 `intel-pipelines` 与
`wiki-writer` agent 消费。

> **v0.2.0 架构变更**：从 webhook 被动接收改为 MTProto 主动监听。
> 原因：目标群组无法加 Bot（群主限制），改用个人账号 API 监听。
> Legacy webhook 端点保留但默认关闭。

---

## 架构

```
Telegram 群组消息 (24/7)
        │
        │ MTProto 长连接 (Telethon)
        ▼
┌─────────────────────────────────────────────┐
│            bridge-ingress (v0.2.0)           │
│                                             │
│  tg_listener.py                             │
│    ├── meme 类监听 (TG_MEME_CHAT_IDS)       │
│    └── contract 类监听 (TG_CONTRACT_CHAT_IDS)│
│         │                                   │
│         ▼                                   │
│  inbox_writer.py → /data/inbox/             │
│  phase_router.py → keywords.yaml 路由       │
│                                             │
│  GET /healthz  (FastAPI, docker 健康检查)    │
└─────────────────────────────────────────────┘
```

**两大监听类别**：

| 类别 | 环境变量 | 用途 |
|---|---|---|
| `meme` | `TG_MEME_CHAT_IDS` | 链上 meme 机会信号群 |
| `contract` | `TG_CONTRACT_CHAT_IDS` | 加密合约/perp 机会信号群 |

每条消息经 phase_router 路由后写入同一 `Telegram-Captures/` 目录，
front-matter 中 `phase` 字段标注路由结果。

---

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `TG_API_ID` | ✅ | — | 从 https://my.telegram.org/apps 获取 |
| `TG_API_HASH` | ✅ | — | 同上 |
| `TG_SESSION_STRING` | ✅ | — | 通过 `generate_session.py` 一次性生成 |
| `TG_MEME_CHAT_IDS` | ⚠️ | — | 逗号分隔的 chat ID 列表（至少一个类别必填） |
| `TG_CONTRACT_CHAT_IDS` | ⚠️ | — | 逗号分隔的 chat ID 列表（至少一个类别必填） |
| `INBOX_PATH` | | `/data/inbox` | 落盘根目录 |
| `KEYWORDS_PATH` | | `/blueprint/.../keywords.yaml` | Phase 路由词典（只读挂载） |
| `LOG_LEVEL` | | `info` | `debug` / `info` / `warning` / `error` |
| `LISTEN_PORT` | | `8080` | 容器内 healthcheck 端口 |
| `TELEGRAM_WEBHOOK_SECRET` | | — | 留空则禁用 legacy webhook 端点 |

> ⚠️ `TG_MEME_CHAT_IDS` 和 `TG_CONTRACT_CHAT_IDS` 至少要设一个，
> 否则启动会报错（没什么可监听的）。

> ⚠️ **绝不**把 `TG_SESSION_STRING`、`TG_API_HASH` 写进任何被 git 跟踪的文件。
> Session string 等同于登录凭据，泄露 = 账号被盗。

---

## 获取 chat ID

Telegram 群组的 chat ID 通常是负数（如 `-1001234567890`）。获取方式：

1. 把 `@userinfobot` 或 `@raw_data_bot` 加进目标群
2. 在群里发任意消息，bot 会回复含 chat ID
3. 或者用 Telethon 脚本：
   ```python
   async for dialog in client.iter_dialogs():
       print(dialog.id, dialog.name)
   ```
4. 把 ID 填入 `.env`：`TG_MEME_CHAT_IDS=-1001234567890,-1009876543210`

---

## 生成 Session String

**仅需执行一次**（在能接收验证码的机器上）：

```bash
export TG_API_ID=12345678
export TG_API_HASH=abcdef1234567890abcdef1234567890
python generate_session.py
```

按提示输入手机号 → 验证码 → (可选 2FA 密码)。脚本会打印一个长字符串，
把它存入 VPS 的 `.env` 文件：

```
TG_SESSION_STRING=1BVtsOH...（很长的字符串）
```

Session 不会过期（除非你在 Telegram 设置里主动终止该 session）。

---

## 文件名格式（有意偏离 Inbox-Processing-Rules）

落盘文件名：

```
YYYY-MM-DD_telegram_<chat_id>_<message_id>.md      (UTC 日期)
```

**有意偏离** Inbox-Processing-Rules 的 topic-slug 格式：

1. **幂等防重复**：同一 `(chat_id, message_id)` 只产生一个文件
2. **不依赖 LLM**：bridge 不在热路径调模型
3. **wiki-writer 后续负责重命名**

---

## front-matter 字段

```yaml
captured_at: 2026-05-20T03:14:15+00:00
source: telegram
source_id: telegram:<chat_id>:<message_id>
chat_id: -1001234567890
message_id: 4242
message_date: 2024-05-06T12:53:20+00:00
from_username: alice
phase: phase_3                                # phase_1/phase_2/phase_3/phase_4 或 null
tags: []
status: raw
priority: p2
owner: intel-summarizer
bridge_version: 0.2.0
```

---

## /healthz 响应

```json
{
  "status": "ok",
  "listener_connected": true,
  "messages_processed": 42
}
```

- `listener_connected: false` 表示 MTProto 连接断了（watchdog 应告警）
- `messages_processed` 是累计计数，重启归零

---

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt pytest httpx

# 跑单元测试（不需要真实 Telegram 凭据）
pytest -q

# Docker 构建
docker build -t bridge-ingress:dev .
```

> 本地测试**不启动真实 MTProto 连接**——测试用 mock 替代 Telethon client。
> 真实连接测试需要有效的 session string，只在 VPS 上做。

---

## 安全与风险

### Userbot 使用须知

- Telegram ToS 允许使用官方 API，但对自动化有频率限制
- **本服务只读不写**：不发消息、不改群设置、不点赞、不转发
- 只读监听被封号的风险极低，但非零
- 建议：不要监听过多群（<20），不要高频调用其他 API

### Session String 安全

- Session string = 完整登录凭据，泄露等于账号被盗
- 只存在 VPS 本地 `.env`，永不入 git
- 定期在 Telegram Settings → Devices 检查活跃 session
- 如果怀疑泄露：立即在 Telegram 设置里终止该 session

---

## 不做（明确边界）

- 不发消息 / 不回复 / 不转发
- 不接 Discord / 飞书（后续 PR）
- 不发布到 GHCR（先本地 `bridge-ingress:dev`）
- 不在日志、注释、测试 fixture 里出现真实 token/session
- 不主动调 Telegram API（除了 `get_me()` 验证连接）

---

## 与 PR #15 的关系

| PR #15 (v0.1.0) | PR #16 (v0.2.0) |
|---|---|
| Webhook 被动接收 | MTProto 主动监听 |
| 需要 Bot 加群 | 用个人账号，不需要群主配合 |
| `TELEGRAM_WEBHOOK_SECRET` 必填 | 可选（留空禁用 webhook） |
| 单一入口 | 两类监听：meme + contract |
| — | `generate_session.py` 工具 |

复用的模块（零改动）：`phase_router.py`、`inbox_writer.py`、
`logger.py`、`signature.py`。
