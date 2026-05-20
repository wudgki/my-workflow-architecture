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
  - start() does NOT raise on connection failure. It stores the error in
    last_error and sets connected=False. The caller (main.py lifespan)
    can proceed without blocking FastAPI startup.

ASCII-only.
"""
from __future__ import annotations

import asyncio
import traceback
from typing import Optional, Tuple

from inbox_writer import write_telegram_capture
from logger import get_logger
from phase_router import PhaseRouter


_BRIDGE_VERSION = "0.2.2"


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
        dc_id: Optional[int] = None,
        server_address: str = "",
        server_port: int = 443,
        proxy: Optional[Tuple] = None,
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
        self._last_error: str = ""
        self._dc_id = dc_id
        self._server_address = server_address
        self._server_port = server_port
        self._proxy = proxy

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def messages_processed(self) -> int:
        return self._messages_processed

    @property
    def last_error(self) -> str:
        return self._last_error

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

        IMPORTANT: This method does NOT raise exceptions. On failure it
        sets self._connected = False and self._last_error with a
        human-readable error string. The caller (main.py) can inspect
        these via /healthz without the HTTP server being blocked.
        """
        try:
            await self._do_start()
        except Exception as exc:
            self._connected = False
            self._last_error = str(exc)
            self._log.error(
                "tg_listener_start_failed",
                extra={"reason": self._last_error},
            )

    async def _do_start(self) -> None:
        """Internal start logic; may raise."""
        from telethon import TelegramClient, events
        from telethon.sessions import StringSession

        self._log.info(
            "tg_listener_starting",
            extra={
                "version": _BRIDGE_VERSION,
                "meme_chats": len(self._meme_ids),
                "contract_chats": len(self._contract_ids),
                "dc_override": bool(self._dc_id and self._server_address),
                "proxy_configured": bool(self._proxy),
            },
        )

        session = StringSession(self._session_string)

        # Apply DC endpoint override if configured.
        if self._dc_id and self._server_address:
            session.set_dc(
                self._dc_id, self._server_address, self._server_port
            )
            self._log.info(
                "tg_listener_dc_override_applied",
                extra={
                    "dc_id": self._dc_id,
                    "server_port": self._server_port,
                },
            )

        # Build client kwargs; add proxy if configured.
        client_kwargs: dict = {}
        if self._proxy:
            client_kwargs["proxy"] = self._proxy

        self._client = TelegramClient(
            session, self._api_id, self._api_hash, **client_kwargs
        )

        self._client.add_event_handler(
            self._on_new_message,
            events.NewMessage(chats=list(self._all_ids)),
        )

        await self._client.connect()
        if not await self._client.is_user_authorized():
            raise RuntimeError(
                "Telegram session not authorized. "
                "Run generate_session.py to create a new session string."
            )

        self._connected = True
        self._last_error = ""
        me = await self._client.get_me()
        self._log.info(
            "tg_listener_connected",
            extra={
                "user_id": me.id if me else None,
                "username": me.username if me else None,
            },
        )

    async def run_until_disconnected(self) -> None:
        """Block until the client disconnects (e.g. on SIGTERM).

        If the client was never connected (start failed), this returns
        immediately without raising.
        """
        if self._client is None or not self._connected:
            return
        try:
            await self._client.run_until_disconnected()
        except Exception as exc:
            self._connected = False
            self._last_error = "disconnected: " + str(exc)
            self._log.warning(
                "tg_listener_disconnected_unexpectedly",
                extra={"reason": self._last_error},
            )

    async def stop(self) -> None:
        """Gracefully disconnect from Telegram."""
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._connected = False
            self._log.info(
                "tg_listener_stopped",
                extra={"messages_processed": self._messages_processed},
            )

    async def _on_new_message(self, event) -> None:
        """Handle a new message from a whitelisted chat.

        This method NEVER raises. All exceptions are caught, logged with
        full context, and the listener continues processing future events.
        """
        chat_id: Optional[int] = None
        message_id: Optional[int] = None

        try:
            chat_id = getattr(event, "chat_id", None)
            message = getattr(event, "message", None)
            message_id = getattr(message, "id", None) if message else None

            # Safe text extraction (avoid deprecated .message alias).
            raw_text = ""
            if message is not None:
                raw_text = getattr(message, "text", None) or ""
                if not raw_text:
                    raw_text = getattr(message, "raw_text", None) or ""

            has_text = bool(raw_text)
            text_length = len(raw_text)

            category = self._categorize(chat_id) if chat_id is not None else None
            is_target = category is not None

            self._log.info(
                "tg_event_received",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "has_text": has_text,
                    "text_length": text_length,
                    "is_target_chat": is_target,
                    "watch_category": category,
                },
            )

            if not is_target:
                self._log.info(
                    "ignored_not_target_chat",
                    extra={"chat_id": chat_id, "message_id": message_id},
                )
                return

            if not has_text:
                self._log.info(
                    "ignored_empty_text",
                    extra={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "watch_category": category,
                    },
                )
                return

            self._router.reload_if_changed()

            # Safe sender lookup.
            sender_username = ""
            sender_id = 0
            try:
                sender = await event.get_sender()
                if sender is not None:
                    sender_username = getattr(sender, "username", "") or ""
                    sender_id = getattr(sender, "id", 0) or 0
            except Exception:
                pass

            # Safe date extraction.
            msg_date = getattr(message, "date", None)
            date_ts = 0
            if msg_date is not None:
                try:
                    date_ts = int(msg_date.timestamp())
                except Exception:
                    date_ts = 0

            payload = {
                "update_id": 0,
                "message": {
                    "message_id": message_id,
                    "date": date_ts,
                    "chat": {"id": chat_id, "type": "supergroup"},
                    "from": {"id": sender_id, "username": sender_username},
                    "text": raw_text,
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
            except Exception as exc:
                self._log.error(
                    "ignored_writer_error",
                    extra={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "watch_category": category,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
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

        except Exception as exc:
            self._log.error(
                "tg_message_handler_error",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
