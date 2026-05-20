"""Unit tests for tg_listener.py (no real Telegram connection).

ASCII-only.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tg_listener import TelegramListener, _parse_chat_ids


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
