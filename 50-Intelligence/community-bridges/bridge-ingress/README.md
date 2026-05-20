# bridge-ingress (v0.2.0, Telegram MTProto Listener)

MTProto userbot that monitors whitelisted Telegram chats, routes via
keywords.yaml, writes Markdown captures to `/data/inbox/Telegram-Captures/`.

> v0.2.0: webhook replaced by MTProto listener (group admin restriction
> prevents adding bots). Legacy webhook kept but disabled by default.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TG_API_ID` | yes | - | From https://my.telegram.org/apps |
| `TG_API_HASH` | yes | - | From https://my.telegram.org/apps |
| `TG_SESSION_STRING` | yes | - | Via `generate_session.py` |
| `TG_MEME_CHAT_IDS` | * | - | Comma-separated chat IDs (meme signals) |
| `TG_CONTRACT_CHAT_IDS` | * | - | Comma-separated chat IDs (contract signals) |
| `INBOX_PATH` | | `/data/inbox` | Write directory |
| `KEYWORDS_PATH` | | see Dockerfile | Phase routing dictionary |
| `LOG_LEVEL` | | `info` | debug/info/warning/error |
| `LISTEN_PORT` | | `8080` | Healthcheck port |
| `TELEGRAM_WEBHOOK_SECRET` | | - | Set to enable legacy webhook |

(*) At least one of MEME or CONTRACT must be non-empty.

## Monitoring Categories

| Category | Env Var | front-matter field |
|---|---|---|
| meme | `TG_MEME_CHAT_IDS` | `watch_category: meme` |
| contract | `TG_CONTRACT_CHAT_IDS` | `watch_category: contract` |

Chat IDs must NOT overlap between categories.

## File Format

```
YYYY-MM-DD_telegram_<chat_id>_<message_id>.md   (UTC)
```

Intentional deviation from Inbox-Processing-Rules (idempotent by design).

### front-matter

```yaml
phase: phase_3
watch_category: meme
chat_id: -1001234567890
message_id: 4242
source: telegram
```

## Local Development

```bash
pip install -r requirements.txt pytest httpx
pytest -q   # no real TG creds needed
```

## Security

- Session string = full login credential. Never enters git.
- Read-only userbot: never sends, modifies, or reacts.
- All .py files are strict ASCII.
