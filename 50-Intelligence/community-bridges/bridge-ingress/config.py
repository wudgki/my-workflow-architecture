"""Environment-driven settings for bridge-ingress.

v0.2.1: Added optional DC override (TG_DC_ID / TG_SERVER_ADDRESS /
TG_SERVER_PORT) and optional SOCKS5 proxy (TG_PROXY_*).

ASCII-only by repo convention.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    # MTProto listener (primary mode)
    tg_api_id: int
    tg_api_hash: str
    tg_session_string: str
    tg_meme_chat_ids: str
    tg_contract_chat_ids: str

    # Optional DC endpoint override (for VPS where default DC is unreachable)
    tg_dc_id: Optional[int]
    tg_server_address: str
    tg_server_port: int

    # Optional SOCKS5 proxy
    tg_proxy_type: str
    tg_proxy_host: str
    tg_proxy_port: Optional[int]
    tg_proxy_username: str
    tg_proxy_password: str

    # Shared
    inbox_path: str
    keywords_path: str
    log_level: str
    listen_port: int

    # Legacy webhook (kept for backward compat)
    telegram_webhook_secret: str


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError("missing required env var: " + name)
    return value


def _opt_int(name: str) -> Optional[int]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(name + " must be an integer if set")


def load_settings() -> Settings:
    """Load settings from process environment."""
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
            "must be set"
        )

    return Settings(
        tg_api_id=tg_api_id,
        tg_api_hash=tg_api_hash,
        tg_session_string=tg_session_string,
        tg_meme_chat_ids=meme_ids,
        tg_contract_chat_ids=contract_ids,
        tg_dc_id=_opt_int("TG_DC_ID"),
        tg_server_address=os.environ.get("TG_SERVER_ADDRESS", ""),
        tg_server_port=int(os.environ.get("TG_SERVER_PORT", "443")),
        tg_proxy_type=os.environ.get("TG_PROXY_TYPE", ""),
        tg_proxy_host=os.environ.get("TG_PROXY_HOST", ""),
        tg_proxy_port=_opt_int("TG_PROXY_PORT"),
        tg_proxy_username=os.environ.get("TG_PROXY_USERNAME", ""),
        tg_proxy_password=os.environ.get("TG_PROXY_PASSWORD", ""),
        inbox_path=os.environ.get("INBOX_PATH", "/data/inbox"),
        keywords_path=os.environ.get(
            "KEYWORDS_PATH",
            "/blueprint/50-Intelligence/pipelines/keywords.yaml",
        ),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        listen_port=int(os.environ.get("LISTEN_PORT", "8080")),
        telegram_webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET", ""),
    )
