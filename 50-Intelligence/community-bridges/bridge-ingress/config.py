"""Environment-driven settings for bridge-ingress.

v0.2.0: Added MTProto listener settings (TG_API_ID, TG_API_HASH,
TG_SESSION_STRING, TG_MEME_CHAT_IDS, TG_CONTRACT_CHAT_IDS).
TELEGRAM_WEBHOOK_SECRET is now optional (only needed if webhook mode
is desired alongside the listener; v2 default is listener-only).

ASCII-only by repo convention. All user-facing prose lives in README.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    # MTProto listener (primary mode in v0.2.0)
    tg_api_id: int
    tg_api_hash: str
    tg_session_string: str
    tg_meme_chat_ids: str       # comma-separated, parsed by tg_listener
    tg_contract_chat_ids: str   # comma-separated, parsed by tg_listener

    # Shared
    inbox_path: str
    keywords_path: str
    log_level: str
    listen_port: int

    # Legacy webhook (kept for backward compat / future hybrid mode)
    telegram_webhook_secret: str


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError("missing required env var: " + name)
    return value


def load_settings() -> Settings:
    """Load settings from process environment.

    Required for MTProto listener mode:
      TG_API_ID, TG_API_HASH, TG_SESSION_STRING

    At least one of TG_MEME_CHAT_IDS or TG_CONTRACT_CHAT_IDS must be
    non-empty (otherwise nothing to monitor).

    TELEGRAM_WEBHOOK_SECRET is optional in v0.2.0 (defaults to empty
    string which disables the webhook endpoint auth check).
    """
    tg_api_id_raw = _require("TG_API_ID")
    try:
        tg_api_id = int(tg_api_id_raw)
    except ValueError:
        raise RuntimeError("TG_API_ID must be an integer")

    tg_api_hash = _require("TG_API_HASH")
    tg_session_string = _require("TG_SESSION_STRING")

    meme_ids = os.environ.get("TG_MEME_CHAT_IDS", "")
    contract_ids = os.environ.get("TG_CONTRACT_CHAT_IDS", "")

    if not meme_ids.strip() and not contract_ids.strip():
        raise RuntimeError(
            "at least one of TG_MEME_CHAT_IDS or TG_CONTRACT_CHAT_IDS "
            "must be set (otherwise nothing to monitor)"
        )

    return Settings(
        tg_api_id=tg_api_id,
        tg_api_hash=tg_api_hash,
        tg_session_string=tg_session_string,
        tg_meme_chat_ids=meme_ids,
        tg_contract_chat_ids=contract_ids,
        inbox_path=os.environ.get("INBOX_PATH", "/data/inbox"),
        keywords_path=os.environ.get(
            "KEYWORDS_PATH",
            "/blueprint/50-Intelligence/pipelines/keywords.yaml",
        ),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        listen_port=int(os.environ.get("LISTEN_PORT", "8080")),
        telegram_webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET", ""),
    )
