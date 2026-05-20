"""Unit tests for tg_listener.py (no real Telegram connection).

Tests cover:
  - _parse_chat_ids utility
  - _categorize logic
  - _on_new_message handler: target chat + valid text, non-target chat,
    empty text, writer exception, handler exception resilience

All tests use fake event/message objects; Telethon is never imported.

ASCII-only.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, patch

import pytest

from tg_listener import TelegramListener, _parse_chat_ids


# --------------------------------------------------------------------- #
# _parse_chat_ids
# --------------------------------------------------------------------- #


def test_parse_chat_ids_basic() -> None:
    assert _parse_chat_ids("-100111,-100222") == [-100111, -100222]


def test_parse_chat_ids_with_spaces() -> None:
    assert _parse_chat_ids(" -100111 , -100222 ") == [-100111, -100222]


def test_parse_chat_ids_empty_string() -> None:
    assert _parse_chat_ids("") == []


def test_parse_chat_ids_skips_non_integers() -> None:
    assert _parse_chat_ids("-100111,abc,-100222") == [-100111, -100222]


def test_parse_chat_ids_single() -> None:
    assert _parse_chat_ids("-100333") == [-100333]


def test_parse_chat_ids_trailing_comma() -> None:
    assert _parse_chat_ids("-100111,") == [-100111]


# --------------------------------------------------------------------- #
# TelegramListener categorization
# --------------------------------------------------------------------- #


@pytest.fixture
def listener(keywords_yaml: Path, inbox_dir: Path) -> TelegramListener:
    return TelegramListener(
        api_id=12345678,
        api_hash="fake_hash_for_unit_tests",
        session_string="will-not-be-used-because-start-is-not-called",
        meme_chat_ids=[-100111, -100222],
        contract_chat_ids=[-100333, -100444],
        inbox_path=str(inbox_dir),
        keywords_path=str(keywords_yaml),
    )


def test_categorize_meme(listener: TelegramListener) -> None:
    assert listener._categorize(-100111) == "meme"
    assert listener._categorize(-100222) == "meme"


def test_categorize_contract(listener: TelegramListener) -> None:
    assert listener._categorize(-100333) == "contract"
    assert listener._categorize(-100444) == "contract"


def test_categorize_unknown(listener: TelegramListener) -> None:
    assert listener._categorize(-999999) is None


def test_initial_state(listener: TelegramListener) -> None:
    assert listener.connected is False
    assert listener.messages_processed == 0


# --------------------------------------------------------------------- #
# Fake event/message for handler tests
# --------------------------------------------------------------------- #


class _FakeMessage:
    """Mimics a Telethon Message object for handler testing."""

    def __init__(
        self,
        msg_id: int = 1,
        text: str = "",
        chat_id: int = -100111,
        date: Any = None,
    ) -> None:
        self.id = msg_id
        self.text = text
        self.raw_text = text
        self.date = date


class _FakeSender:
    def __init__(self, user_id: int = 42, username: str = "tester") -> None:
        self.id = user_id
        self.username = username


class _FakeEvent:
    """Mimics a Telethon NewMessage.Event for handler testing."""

    def __init__(
        self,
        chat_id: int = -100111,
        message: Optional[_FakeMessage] = None,
        sender: Optional[_FakeSender] = None,
    ) -> None:
        self.chat_id = chat_id
        self.message = message or _FakeMessage(chat_id=chat_id)
        self._sender = sender or _FakeSender()

    async def get_sender(self) -> Optional[_FakeSender]:
        return self._sender


# --------------------------------------------------------------------- #
# _on_new_message handler tests
# --------------------------------------------------------------------- #


class TestOnNewMessage:
    """Tests for the _on_new_message handler."""

    def _run(self, coro) -> None:
        """Helper to run async test methods."""
        asyncio.run(coro)

    def test_target_chat_valid_text_writes_file(
        self, listener: TelegramListener, inbox_dir: Path
    ) -> None:
        """Target chat + valid text -> file written, messages_processed +1."""
        from datetime import datetime, timezone

        msg = _FakeMessage(
            msg_id=42,
            text="BTC perp breakout signal",
            chat_id=-100111,
            date=datetime(2026, 5, 20, tzinfo=timezone.utc),
        )
        event = _FakeEvent(chat_id=-100111, message=msg)

        self._run(listener._on_new_message(event))

        assert listener.messages_processed == 1
        captures_dir = inbox_dir / "Telegram-Captures"
        files = list(captures_dir.iterdir())
        assert len(files) == 1
        body = files[0].read_text(encoding="utf-8")
        assert "chat_id: -100111" in body
        assert "message_id: 42" in body
        assert "watch_category: meme" in body
        assert "source: telegram" in body
        assert "BTC perp breakout signal" in body

    def test_non_target_chat_ignored(
        self, listener: TelegramListener, inbox_dir: Path
    ) -> None:
        """Non-target chat_id -> ignored, no file, messages_processed = 0."""
        msg = _FakeMessage(
            msg_id=99, text="some text", chat_id=-999999
        )
        event = _FakeEvent(chat_id=-999999, message=msg)

        self._run(listener._on_new_message(event))

        assert listener.messages_processed == 0
        captures_dir = inbox_dir / "Telegram-Captures"
        if captures_dir.exists():
            assert list(captures_dir.iterdir()) == []

    def test_empty_text_ignored(
        self, listener: TelegramListener, inbox_dir: Path
    ) -> None:
        """Target chat but empty text -> ignored, no file."""
        msg = _FakeMessage(msg_id=77, text="", chat_id=-100111)
        event = _FakeEvent(chat_id=-100111, message=msg)

        self._run(listener._on_new_message(event))

        assert listener.messages_processed == 0
        captures_dir = inbox_dir / "Telegram-Captures"
        if captures_dir.exists():
            assert list(captures_dir.iterdir()) == []

    def test_writer_exception_does_not_kill_listener(
        self, listener: TelegramListener, inbox_dir: Path
    ) -> None:
        """Writer raising -> logged as ignored_writer_error, listener alive."""
        from datetime import datetime, timezone

        msg = _FakeMessage(
            msg_id=88,
            text="BTC perp signal",
            chat_id=-100111,
            date=datetime(2026, 5, 20, tzinfo=timezone.utc),
        )
        event = _FakeEvent(chat_id=-100111, message=msg)

        with patch(
            "tg_listener.write_telegram_capture",
            side_effect=RuntimeError("disk full"),
        ):
            self._run(listener._on_new_message(event))

        # Listener did not crash; messages_processed stays 0.
        assert listener.messages_processed == 0

    def test_handler_exception_does_not_kill_listener(
        self, listener: TelegramListener
    ) -> None:
        """Any unexpected exception in handler -> caught, listener alive."""
        # Event with no message attribute at all (extreme edge case).
        class _BrokenEvent:
            chat_id = -100111

            @property
            def message(self):
                raise AttributeError("broken event")

            async def get_sender(self):
                return None

        self._run(listener._on_new_message(_BrokenEvent()))

        # Listener did not crash.
        assert listener.messages_processed == 0

    def test_sender_lookup_failure_still_writes(
        self, listener: TelegramListener, inbox_dir: Path
    ) -> None:
        """Sender lookup fails -> still writes file with empty sender."""
        from datetime import datetime, timezone

        msg = _FakeMessage(
            msg_id=55,
            text="Polymarket odds shift",
            chat_id=-100333,
            date=datetime(2026, 5, 20, tzinfo=timezone.utc),
        )

        class _EventWithBrokenSender:
            chat_id = -100333
            message = msg

            async def get_sender(self):
                raise RuntimeError("sender lookup failed")

        self._run(listener._on_new_message(_EventWithBrokenSender()))

        assert listener.messages_processed == 1
        captures_dir = inbox_dir / "Telegram-Captures"
        files = list(captures_dir.iterdir())
        assert len(files) == 1
        body = files[0].read_text(encoding="utf-8")
        assert "watch_category: contract" in body


# --------------------------------------------------------------------- #
# Integration tests (skipped unless RUN_TG_INTEGRATION=1)
# --------------------------------------------------------------------- #


_SKIP_REASON = (
    "Real Telegram integration test. Set RUN_TG_INTEGRATION=1 and "
    "provide TG_API_ID / TG_API_HASH / TG_SESSION_STRING to run."
)


@pytest.mark.skipif(
    os.environ.get("RUN_TG_INTEGRATION") != "1",
    reason=_SKIP_REASON,
)
class TestTelegramIntegration:
    def test_connect_and_disconnect(self) -> None:
        import asyncio
        asyncio.run(self._connect_and_disconnect())

    async def _connect_and_disconnect(self) -> None:
        listener = TelegramListener(
            api_id=int(os.environ["TG_API_ID"]),
            api_hash=os.environ["TG_API_HASH"],
            session_string=os.environ["TG_SESSION_STRING"],
            meme_chat_ids=_parse_chat_ids(
                os.environ.get("TG_MEME_CHAT_IDS", "")
            ),
            contract_chat_ids=_parse_chat_ids(
                os.environ.get("TG_CONTRACT_CHAT_IDS", "")
            ),
            inbox_path="/tmp/test-inbox",
            keywords_path="/dev/null",
        )
        await listener.start()
        assert listener.connected is True
        await listener.stop()
        assert listener.connected is False
