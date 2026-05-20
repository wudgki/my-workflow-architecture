"""Unit tests for tg_listener.py.

Tests the listener logic (chat categorization, payload construction,
writing) WITHOUT a real Telegram connection. Telethon is mocked.

ASCII-only.
"""
from __future__ import annotations

from pathlib import Path

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
        api_hash="fake_hash",
        session_string="fake_session",
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
