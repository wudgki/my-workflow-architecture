"""Structured JSON logger with hard-coded field whitelist.

Why a whitelist instead of just "log everything in record.__dict__":
this service handles webhook payloads that may contain bot tokens,
chat content, and other sensitive material. A typo like
log.info("...", extra={"secret": s}) should not be able to leak the
secret into stdout. Only the named fields below are emitted; anything
else is silently dropped.

ASCII-only.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Fields permitted in JSON log lines beyond the always-emitted ts/level/
# logger/msg. Adding a new field requires a deliberate edit here, which
# forces a code review of what is being logged.
_ALLOWED_FIELDS = frozenset(
    {
        "req_id",
        "source",
        "phase",
        "file",
        "latency_ms",
        "chat_id",
        "message_id",
        "remote_ip",
        "reason",
        "errno",
        "version",
    }
)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _ALLOWED_FIELDS and key not in out:
                out[key] = value
        # ensure_ascii=True (default) escapes any non-ASCII bytes that
        # might sneak in via misuse, keeping log lines safe for any
        # downstream collector.
        return json.dumps(out, separators=(",", ":"))


_INITIALIZED = False


def init_logger(level: str = "info") -> None:
    """Initialize the root logger exactly once."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Quiet uvicorn's default access log noise; we have our own info line.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
