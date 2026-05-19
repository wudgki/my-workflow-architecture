"""Write Telegram captures to /data/inbox/Telegram-Captures/.

Filename format (intentional deviation from
00-Inbox/Inbox-Processing-Rules.md):

    YYYY-MM-DD_telegram_<chat_id>_<message_id>.md   (UTC date)

Why deviate:
  * Telegram retries webhook delivery on any non-2xx or timeout. The
    same (chat_id, message_id) pair MUST land at the same path so a
    redelivery overwrites identical bytes instead of producing a
    duplicate file.
  * The Inbox-Processing-Rules topic-slug form is a human-readable name.
    Generating one at ingest time would require running an LLM on the
    bridge's hot path, which contradicts the "stateless, no upstream
    calls" charter of bridge-ingress.

The future wiki-writer agent (20-Claude-Code/agents/wiki-writer.md) is
responsible for renaming captures to the canonical topic-slug form when
promoting them into the Wiki. Until then, downstream consumers should
treat the chat_id/message_id filename as opaque and rely on the
front-matter for routing.

ASCII-only.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import yaml

from phase_router import PhaseRouter


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_text(message: dict[str, Any]) -> str:
    """Return text or caption from a Telegram Message; empty string if none."""
    text = message.get("text")
    if isinstance(text, str) and text:
        return text
    caption = message.get("caption")
    if isinstance(caption, str) and caption:
        return caption
    return ""


def write_telegram_capture(
    payload: dict[str, Any],
    inbox_path: str,
    phase_router: PhaseRouter,
    bridge_version: str,
) -> dict[str, Any]:
    """Write one Telegram update to disk.

    Returns:
        dict with keys: phase (int|None), file (absolute path),
        chat_id (int), message_id (int).

    Raises:
        ValueError if `payload` is not a usable Telegram message update.
        v1 only handles `message` updates; edited_message / channel_post /
        callback_query etc. are rejected and the caller decides how to
        respond (typically: log and 200 to suppress retries).
    """
    if not isinstance(payload, dict):
        raise ValueError("payload not a dict")

    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("no message field")

    chat = message.get("chat") or {}
    chat_id = _safe_int(chat.get("id"))
    message_id = _safe_int(message.get("message_id"))
    date_unix = _safe_int(message.get("date"))

    if chat_id is None or message_id is None:
        raise ValueError("missing chat.id or message_id")

    text = _coerce_text(message)
    phase = phase_router.route(text)

    captured_at = (
        datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()
    )
    if date_unix is not None:
        message_dt_iso = (
            datetime.fromtimestamp(date_unix, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )
    else:
        message_dt_iso = ""

    date_part = captured_at[:10]
    filename = (
        date_part
        + "_telegram_"
        + str(chat_id)
        + "_"
        + str(message_id)
        + ".md"
    )

    target_dir = os.path.join(inbox_path, "Telegram-Captures")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, filename)

    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    sender_username = sender.get("username") if isinstance(sender, dict) else None

    front_matter = {
        "captured_at": captured_at,
        "source": "telegram",
        "source_id": "telegram:" + str(chat_id) + ":" + str(message_id),
        "chat_id": chat_id,
        "message_id": message_id,
        "message_date": message_dt_iso,
        "from_username": sender_username or "",
        "phase": phase,
        "tags": [],
        "status": "raw",
        "priority": "p2",
        "owner": "intel-summarizer",
        "bridge_version": bridge_version,
    }

    body_text = text if text else "_(no text)_"

    front_yaml = yaml.safe_dump(
        front_matter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip("\n")

    content = (
        "---\n"
        + front_yaml
        + "\n---\n"
        + "\n"
        + "# Telegram capture\n"
        + "\n"
        + body_text
        + "\n"
    )

    # Atomic-ish write within the same volume: write a sibling .tmp then
    # os.replace. Idempotent: a redelivery overwrites identical bytes.
    tmp_path = target_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.replace(tmp_path, target_path)

    return {
        "phase": phase,
        "file": target_path,
        "chat_id": chat_id,
        "message_id": message_id,
    }
