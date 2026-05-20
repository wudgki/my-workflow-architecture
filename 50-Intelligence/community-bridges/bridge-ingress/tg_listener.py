"""Telegram MTProto listener using Telethon.

Connects as a userbot (personal account via api_id + api_hash + session)
and listens for new messages in whitelisted chats. Two monitoring
categories are supported:

  - meme: on-chain meme opportunity signals (TG_MEME_CHAT_IDS)
  - contract: crypto contract/perp opportunity signals (TG_CONTRACT_CHAT_IDS)

Design notes:
  - Read-only: never sends messages, never modifies chats, never reacts.
  - Low-frequency: one event handler, no polling loops.
  - Graceful shutdown: disconnect on SIGTERM/SIGINT (docker stop).
  - The Telethon client is ONLY created inside start(). __init__ does
    NOT touch Telethon, making the class safe to instantiate in tests.

ASCII-only.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from inbox_writer import write_telegram_capture
from logger import get_logger
from phase_router import PhaseRouter


_BRIDGE_VERSION = "0.2.0"


def _parse_chat_ids(raw: str) -> list[int]:
    """Parse comma-separated chat IDs. Skips blanks and non-integers."""
    result: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


class TelegramListener:
    """Async Telegram MTProto listener with chat whitelist.

    __init__ does NOT create a Telethon client or StringSession. Those
    are deferred to start(), so tests can instantiate this class freely
    without importing or triggering Telethon validation.
    """

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_string: str,
        meme_chat_ids: list[int],
        contract_chat_ids: list[int],
        inbox_path: str,
        keywords_path: str,
    ) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._session_string = session_string
        self._meme_ids = set(meme_chat_ids)
        self._contract_ids = set(contract_chat_ids)
        self._all_ids = self._meme_ids | self._contract_ids
        self._inbox_path = inbox_path
        self._router = PhaseRouter(keywords_path)
        self._log = get_logger("tg-listener")
        self._client = None  # created in start()
        self._connected = False
        self._messages_processed = 0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def messages_processed(self) -> int:
        return self._messages_processed

    def _categorize(self, chat_id: int) -> Optional[str]:
        """Return monitoring category for a chat, or None if not whitelisted."""
        if chat_id in self._meme_ids:
            return "meme"
        if chat_id in self._contract_ids:
            return "contract"
        return None

    async def start(self) -> None:
        """Connect to Telegram and register the message handler.

        This is the ONLY method that imports and uses Telethon.
        """
        from telethon import TelegramClient, events
        from telethon.sessions import StringSession

        self._log.info(
            "tg_listener_starting",
            extra={
                "version": _BRIDGE_VERSION,
                "meme_chats": len(self._meme_ids),
                "contract_chats": len(self._contract_ids),
            },
        )

        self._client = TelegramClient(
            StringSession(self._session_string),
            self._api_id,
            self._api_hash,
        )

        self._client.add_event_handler(
            self._on_new_message,
            events.NewMessage(chats=list(self._all_ids)),
        )

        await self._client.connect()
        if not await self._client.is_user_authorized():
            self._log.error(
                "tg_listener_not_authorized",
                extra={
                    "reason": "session expired or invalid, "
                    "regenerate via generate_session.py"
                },
            )
            raise RuntimeError(
                "Telegram session not authorized. "
                "Run generate_session.py to create a new session string."
            )

        self._connected = True
        me = await self._client.get_me()
        self._log.info(
            "tg_listener_connected",
            extra={
                "user_id": me.id if me else None,
                "username": me.username if me else None,
            },
        )

    async def run_until_disconnected(self) -> None:
        """Block until the client disconnects (e.g. on SIGTERM)."""
        if self._client is None:
            raise RuntimeError("call start() first")
        await self._client.run_until_disconnected()

    async def stop(self) -> None:
        """Gracefully disconnect from Telegram."""
        if self._client is not None:
            await self._client.disconnect()
            self._connected = False
            self._log.info(
                "tg_listener_stopped",
                extra={"messages_processed": self._messages_processed},
            )

    async def _on_new_message(self, event) -> None:
        """Handle a new message from a whitelisted chat."""
        message = event.message
        chat_id = event.chat_id
        category = self._categorize(chat_id)

        if category is None:
            return

        self._router.reload_if_changed()

        text = message.text or message.message or ""

        sender = await event.get_sender()
        sender_username = ""
        sender_id = 0
        if sender is not None:
            sender_username = getattr(sender, "username", "") or ""
            sender_id = getattr(sender, "id", 0) or 0

        payload = {
            "update_id": 0,
            "message": {
                "message_id": message.id,
                "date": int(message.date.timestamp()) if message.date else 0,
                "chat": {"id": chat_id, "type": "supergroup"},
                "from": {"id": sender_id, "username": sender_username},
                "text": text,
            },
        }

        try:
            result = write_telegram_capture(
                payload=payload,
                inbox_path=self._inbox_path,
                phase_router=self._router,
                bridge_version=_BRIDGE_VERSION,
                watch_category=category,
            )
        except ValueError as exc:
            self._log.warning(
                "tg_listener_message_skipped",
                extra={
                    "chat_id": chat_id,
                    "message_id": message.id,
                    "category": category,
                    "reason": str(exc),
                },
            )
            return

        self._messages_processed += 1
        self._log.info(
            "tg_listener_capture_written",
            extra={
                "source": "telegram",
                "category": category,
                "phase": result["phase"],
                "file": result["file"],
                "chat_id": result["chat_id"],
                "message_id": result["message_id"],
            },
        )
