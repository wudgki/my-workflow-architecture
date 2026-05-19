# bridge-ingress Interface Specification

> 状态：**DRAFT** — 设计文档，尚无实现代码
> 版本：0.1.0
> 日期：2026-05-19
> 关联 PR：#14（本文档）、#12（docker-compose 模板）

本文档定义 `bridge-ingress` 服务的最小可行接口，用于指导后续实现。
Bridge-ingress 是 Hermes VPS 上第一个落地的业务服务，负责接收外部平台的 webhook 推送并写入 `00-Inbox/` 标准格式文件。

---

## 一、服务定位

```
[Discord / Telegram / Feishu webhook]
        |
        v (HTTPS via Cloudflare Tunnel)
+------------------+
| bridge-ingress   |   容器内 :8080
| (this service)   |   写入 /data/inbox/
+------------------+
        |
        v
/data/inbox/<source>-Captures/YYYY-MM-DD_<source>_<topic>.md
```

**职责边界**：

- ✅ 接收 webhook payload
- ✅ 验证来源签名（防伪造）
- ✅ 转为标准 capture 文件写入磁盘
- ✅ 用 keywords.yaml 做初步 Phase 路由（打 `phase` 标签）
- ✅ 暴露 healthz 端点
- ❌ 不做深度 NLP / 摘要（那是 intel-pipelines 的事）
- ❌ 不做 Wiki 写入（那是 wiki-writer agent 的事）
- ❌ 不做交易决策
- ❌ 不主动推送通知（那是 watchdog 的事）

---

## 二、HTTP 端点

| Method | Path | 用途 | 认证 |
|---|---|---|---|
| GET | `/healthz` | 健康检查 | 无 |
| POST | `/webhook/discord` | 接收 Discord webhook | Discord signature 校验 |
| POST | `/webhook/telegram` | 接收 Telegram Bot update | Telegram secret_token header |
| POST | `/webhook/feishu` | 接收飞书事件回调 | Feishu signature 校验 |

### 2.1 `/healthz`

```
GET /healthz

Response 200:
{
  "status": "ok",
  "uptime_sec": 3600,
  "version": "0.1.0",
  "inbox_path": "/data/inbox",
  "keywords_loaded": true,
  "last_capture_at": "2026-05-19T14:32:00Z"
}

Response 503 (unhealthy):
{
  "status": "unhealthy",
  "reason": "inbox_path not writable"
}
```

Docker compose healthcheck 配置：
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
  interval: 30s
  timeout: 5s
  retries: 3
```

### 2.2 `/webhook/discord`

接收 Discord Interactions outgoing webhook（HTTP POST）。

**范围说明**：
- v1 只支持 Discord Interactions request（Application Command / Message Component 等）
- Discord Gateway events 属于 WebSocket 长连接，不属于 HTTP webhook，不在本服务范围
- 如需 Gateway events（如实时消息监听），后续需单独设计 worker/service

**请求验证**：
- 检查 `X-Signature-Ed25519` + `X-Signature-Timestamp` headers
- 使用 Discord Application Public Key（`DISCORD_PUBLIC_KEY` 环境变量）验证签名
- 验证失败 → 返回 401，不写盘

### 2.3 `/webhook/telegram`

接收 Telegram Bot Webhook updates。

**请求验证**：
- 检查 `X-Telegram-Bot-Api-Secret-Token` header
- 与 `TELEGRAM_WEBHOOK_SECRET` 环境变量比对
- 验证失败 → 返回 401，不写盘

**注意**：`TELEGRAM_BOT_TOKEN` 仅在调用 `setWebhook` API 注册端点时需要，服务运行时验签只用 `TELEGRAM_WEBHOOK_SECRET`。

### 2.4 `/webhook/feishu`

接收飞书事件订阅回调。

**请求验证**：
- 使用 `FEISHU_VERIFICATION_TOKEN` 验证请求来源
- 如启用消息加密，使用 `FEISHU_ENCRYPT_KEY` 解密 body
- 处理飞书的 `url_verification` challenge 请求（返回 challenge token）
- 验证失败 → 返回 401，不写盘

---

## 三、落盘路径与文件格式

### 3.1 路径规范

```
/data/inbox/<source>-Captures/YYYY-MM-DD_<source>_<short-topic>.md
```

与 `00-Inbox/Inbox-Processing-Rules.md` 的命名约定完全一致。

映射关系：

| Webhook 来源 | `<source>` | 落地子目录 |
|---|---|---|
| Discord | `discord` | `/data/inbox/Discord-Captures/` |
| Telegram | `telegram` | `/data/inbox/Telegram-Captures/` |
| Feishu | `feishu` | `/data/inbox/Feishu-Captures/` |

### 3.2 文件内容（Markdown + YAML front-matter）

```markdown
---
captured_at: 2026-05-19T14:32:00+00:00
source: telegram
source_id: "group-name/channel-id"
phase: 3
tags: [crypto, kol, perp]
status: new
priority: 2
owner: hermes
bridge_version: "0.1.0"
message_id: "msg_abc123"
---

# <自动生成的短标题>

<原始消息正文，保留格式>

---
_Bridge metadata: processed in 12ms, keywords matched: ["BTC", "perp"]_
```

### 3.3 文件名生成规则

```
YYYY-MM-DD_<source>_<topic-slug>.md
```

- `YYYY-MM-DD`：消息时间戳的日期部分（UTC）
- `<source>`：`discord` / `telegram` / `feishu`
- `<topic-slug>`：从消息正文提取前 5 个关键词，kebab-case 连接，最长 50 字符
- 如果同一秒有重复文件名：追加 `-2` / `-3` 后缀

---

## 四、Phase 路由集成

### 4.1 关键词匹配

- 启动时加载 `/blueprint/50-Intelligence/pipelines/keywords.yaml`
- 对每条消息正文做 case-insensitive substring match
- 按 `phase_1 → phase_2 → phase_3 → phase_4` 顺序，first-match-wins
- 命中 phase 的 exclude 列表 → 跳过该 phase
- 命中 global_exclude → `phase: null`
- 全部不命中 → `phase: null`

### 4.2 热重载

- 每 5 分钟检查 keywords.yaml 的 mtime
- 如果变化，重新加载（不重启服务）
- 加载失败时保留旧版本，写日志告警

---

## 五、日志格式

使用 **structured JSON**，每行一个 JSON 对象：

```json
{"ts":"2026-05-19T14:32:00.123Z","level":"info","msg":"capture written","source":"telegram","phase":3,"file":"2026-05-19_telegram_btc-perp-signal.md","latency_ms":12}
{"ts":"2026-05-19T14:32:01.456Z","level":"warn","msg":"signature verification failed","source":"discord","remote_ip":"1.2.3.4"}
{"ts":"2026-05-19T14:32:02.789Z","level":"error","msg":"inbox path not writable","path":"/data/inbox","errno":"EACCES"}
```

**字段约定**：

| 字段 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `ts` | ISO8601 | 是 | UTC 时间戳 |
| `level` | string | 是 | `debug` / `info` / `warn` / `error` |
| `msg` | string | 是 | 人类可读消息 |
| `source` | string | 否 | `discord` / `telegram` / `feishu` |
| `phase` | int/null | 否 | 路由结果 |
| `file` | string | 否 | 写入的文件名 |
| `latency_ms` | int | 否 | 处理耗时 |
| `remote_ip` | string | 否 | 请求来源 IP |
| `errno` | string | 否 | 系统错误码 |

日志写到 `/logs/bridge-ingress.log`（容器内），由 docker 日志驱动收集。

---

## 六、失败策略

### 6.1 请求级失败

| 失败类型 | 处理 | HTTP 响应 |
|---|---|---|
| 签名校验失败 | 丢弃，记录 warn 日志 | 401 |
| JSON 解析失败 | 丢弃，记录 warn 日志 | 400 |
| 消息为空 | 丢弃，记录 info 日志 | 204 |
| Inbox 路径不可写 | 返回错误，healthz 标记 unhealthy | 500 |
| 文件写入失败 | 重试 1 次，仍失败则返回 500 | 500 |

### 6.2 服务级失败

| 场景 | 行为 |
|---|---|
| 服务 OOM / crash | Docker `restart: on-failure:5` 自动重启，5 次后停止 |
| Inbox 磁盘满 | healthz 返回 503，watchdog 告警 |
| keywords.yaml 加载失败 | 保留旧版本继续服务，日志 error |
| Cloudflare Tunnel 断连 | bridge 无流量进来，自然停止处理；tunnel 恢复后自动恢复 |

### 6.3 死信策略（v1 暂不实现）

v1 不实现死信队列。如果消息丢失（crash + 未写盘），该消息就丢了。
后续版本可加：先写 WAL 再处理，确保 at-least-once。

---

## 七、环境变量

| 变量 | 必须 | 默认值 | 说明 |
|---|---|---|---|
| `INBOX_PATH` | 是 | `/data/inbox` | capture 文件写入根目录 |
| `KEYWORDS_PATH` | 是 | - | keywords.yaml 的完整路径 |
| `DISCORD_PUBLIC_KEY` | 是 | - | Discord Application Public Key（用于 Interactions 签名校验） |
| `TELEGRAM_WEBHOOK_SECRET` | 是 | - | 校验 `X-Telegram-Bot-Api-Secret-Token` header |
| `TELEGRAM_BOT_TOKEN` | 否 | - | 仅在设置 webhook 或主动调用 Bot API 时需要（v1 可暂不填） |
| `FEISHU_VERIFICATION_TOKEN` | 是 | - | 飞书事件订阅 Verification Token |
| `FEISHU_ENCRYPT_KEY` | 否 | - | 飞书事件订阅 Encrypt Key（启用加密时必填） |
| ~~`FEISHU_WEBHOOK_SECRET`~~ | - | - | PR #12 `.env.example` 占位名，实现 PR 应映射到上述两个变量 |
| `LOG_LEVEL` | 否 | `info` | `debug` / `info` / `warn` / `error` |
| `LISTEN_PORT` | 否 | `8080` | HTTP 监听端口 |
| `KEYWORDS_RELOAD_SEC` | 否 | `300` | keywords.yaml 热重载间隔（秒） |

---

## 八、技术选型约束（暂不决定）

以下选型留给实现 PR 决定，本设计文档不锁定：

- **语言**：Python (FastAPI) / Go (net/http) / TypeScript (Hono/Express) 均可
- **镜像大小**：目标 < 100MB（alpine base）
- **构建方式**：Dockerfile multi-stage
- **测试**：至少覆盖签名校验 + Phase 路由 + 文件写入

---

## 九、与其它组件的接口契约

| 组件 | 接口点 | 方向 | 格式 |
|---|---|---|---|
| Cloudflare Tunnel | `:8080` | 入 | HTTP POST (webhook payload) |
| keywords.yaml | 文件系统 | 入（只读） | YAML |
| /data/inbox/ | 文件系统 | 出（只写） | Markdown + YAML front-matter |
| Docker healthcheck | `:8080/healthz` | 入 | HTTP GET |
| watchdog | `:8080/healthz` | 入 | HTTP GET（间接，通过 docker API） |
| intel-pipelines | /data/inbox/ | 无直接调用 | 通过共享 volume 解耦 |
| VPS-to-primary sync | /data/inbox/ | 出（未来） | SSH rsync 定时拉取到主电脑（尚未实现，后续 PR） |

---

## 十、验收标准（实现 PR 的 DoD）

实现代码的 PR 必须满足：

- [ ] 三个 webhook 端点全部可接收 payload
- [ ] 签名校验正确（每个来源至少 1 个 integration test）
- [ ] 写入的文件符合第三节格式规范
- [ ] Phase 路由与 keywords.yaml 一致（unit test）
- [ ] healthz 正常 + 异常两个 case 覆盖
- [ ] docker compose config 通过（替换 placeholder tag）
- [ ] 镜像推到 GHCR
- [ ] 端到端 smoke test：cloudflared + bridge-ingress 一起跑，从外部发 webhook 验证 capture 落盘

---

<!--
维护说明：
- 实现过程中如果发现需要修改本 spec，先更新本文件再改代码
- 本文件是"接口契约"，上下游（intel-pipelines / watchdog / Init 脚本）依赖它
- 不要在本文件写实现细节（框架选型 / 内部模块拆分），那些放在代码仓的 README 里
-->
