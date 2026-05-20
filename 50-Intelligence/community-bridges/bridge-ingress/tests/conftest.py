"""Shared pytest fixtures for bridge-ingress tests.

IMPORTANT: _BRIDGE_SKIP_AUTO_CREATE is set at import time (before any
test runs) so that importing main.py never triggers the real app factory.

ASCII-only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Prevent main.py module-level create_app() from running when any test
# imports main (directly or transitively). MUST be set before import.
os.environ.setdefault("_BRIDGE_SKIP_AUTO_CREATE", "1")

# Put the bridge-ingress/ package directory on sys.path.
_BRIDGE_DIR = Path(__file__).resolve().parent.parent
if str(_BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_DIR))


_FAKE_SECRET = "fake-secret-for-tests-do-not-use"
_FAKE_API_ID = "12345678"
_FAKE_API_HASH = "abcdef1234567890abcdef1234567890"
_FAKE_SESSION = "fake-session-string-for-tests"


@pytest.fixture
def fake_secret() -> str:
    return _FAKE_SECRET


@pytest.fixture
def keywords_yaml(tmp_path: Path) -> Path:
    """A small but realistic keywords.yaml exercising all four phases."""
    content = (
        "phase_1:\n"
        "  label: Infra\n"
        "  include: [hermes, mcp, claude code]\n"
        "  exclude: []\n"
        "phase_2:\n"
        "  label: B2B\n"
        "  include: [jinguan, packaging, b2b]\n"
        "  exclude: []\n"
        "phase_3:\n"
        "  label: Crypto\n"
        "  include: [btc, perp, kol]\n"
        "  exclude: [paper trade]\n"
        "phase_4:\n"
        "  label: Prediction\n"
        "  include: [polymarket, kalshi]\n"
        "  exclude: []\n"
        "global_exclude: [please ignore, smoke noise]\n"
    )
    path = tmp_path / "keywords.yaml"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def inbox_dir(tmp_path: Path) -> Path:
    d = tmp_path / "inbox"
    d.mkdir()
    return d


@pytest.fixture
def app_env(
    monkeypatch: pytest.MonkeyPatch,
    fake_secret: str,
    keywords_yaml: Path,
    inbox_dir: Path,
):
    """Patch env vars so config.load_settings() works in tests."""
    monkeypatch.setenv("TG_API_ID", _FAKE_API_ID)
    monkeypatch.setenv("TG_API_HASH", _FAKE_API_HASH)
    monkeypatch.setenv("TG_SESSION_STRING", _FAKE_SESSION)
    monkeypatch.setenv("TG_MEME_CHAT_IDS", "-100111,-100222")
    monkeypatch.setenv("TG_CONTRACT_CHAT_IDS", "-100333")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", fake_secret)
    monkeypatch.setenv("KEYWORDS_PATH", str(keywords_yaml))
    monkeypatch.setenv("INBOX_PATH", str(inbox_dir))
    monkeypatch.setenv("LOG_LEVEL", "warning")
    monkeypatch.setenv("_BRIDGE_SKIP_AUTO_CREATE", "1")
    yield
