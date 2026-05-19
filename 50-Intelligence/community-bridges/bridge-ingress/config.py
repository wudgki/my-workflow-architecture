"""Environment-driven settings for bridge-ingress.

ASCII-only by repo convention. All user-facing prose lives in README.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_webhook_secret: str
    inbox_path: str
    keywords_path: str
    log_level: str
    listen_port: int


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError("missing required env var: " + name)
    return value


def load_settings() -> Settings:
    """Load settings from process environment.

    TELEGRAM_WEBHOOK_SECRET is the only mandatory variable. The rest fall
    back to the same defaults documented in SPEC-bridge-ingress.md so a
    container started with only the secret will still work in production.
    """
    return Settings(
        telegram_webhook_secret=_require("TELEGRAM_WEBHOOK_SECRET"),
        inbox_path=os.environ.get("INBOX_PATH", "/data/inbox"),
        keywords_path=os.environ.get(
            "KEYWORDS_PATH",
            "/blueprint/50-Intelligence/pipelines/keywords.yaml",
        ),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        listen_port=int(os.environ.get("LISTEN_PORT", "8080")),
    )
