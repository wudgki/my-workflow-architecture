"""Shared pytest fixtures for bridge-ingress tests.

ASCII-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Put the bridge-ingress/ package directory on sys.path so tests can
# import flat modules: `from main import app`, `from signature import ...`.
_BRIDGE_DIR = Path(__file__).resolve().parent.parent
if str(_BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_DIR))


_FAKE_SECRET = "fake-secret-for-tests-do-not-use"


@pytest.fixture
def fake_secret() -> str:
    return _FAKE_SECRET


@pytest.fixture
def keywords_yaml(tmp_path: Path) -> Path:
    """A small but realistic keywords.yaml exercising all four phases.

    Stays separate from the production 50-Intelligence/pipelines/keywords.yaml
    so unit tests are not coupled to changes in the keyword dictionary.
    """
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
    """Patch env vars before main.py is imported by the e2e test client."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", fake_secret)
    monkeypatch.setenv("KEYWORDS_PATH", str(keywords_yaml))
    monkeypatch.setenv("INBOX_PATH", str(inbox_dir))
    monkeypatch.setenv("LOG_LEVEL", "warning")
    yield
