"""Unit tests for extract-keywords.py.

ASCII-only.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_PIPELINES_DIR = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _PIPELINES_DIR / "extract-keywords.py"

_SPEC = importlib.util.spec_from_file_location(
    "extract_keywords", str(_SCRIPT_PATH)
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

generate_keyword_report = _MOD.generate_keyword_report


def _write_capture(
    tmp_path: Path,
    filename: str,
    text: str = "BTC pump signal",
    watch_category: str = "meme",
) -> None:
    content = (
        "---\n"
        "captured_at: 2026-05-20T03:14:15+00:00\n"
        "source: telegram\n"
        "chat_id: -100111\n"
        "message_id: 1\n"
        "phase: null\n"
        f"watch_category: {watch_category}\n"
        "status: raw\n"
        "---\n"
        "\n"
        "# Telegram capture\n"
        "\n"
        f"{text}\n"
    )
    (tmp_path / filename).write_text(content, encoding="utf-8")


def test_empty_dir(tmp_path: Path) -> None:
    report = generate_keyword_report(str(tmp_path))
    assert "No .md files" in report


def test_nonexistent_dir() -> None:
    report = generate_keyword_report("/nonexistent/xyz")
    assert "ERROR" in report


def test_basic_token_extraction(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "BTC pump signal moon lambo",
                   watch_category="meme")
    _write_capture(tmp_path, "b.md", "ETH perp funding rate positive",
                   watch_category="contract")
    report = generate_keyword_report(str(tmp_path))
    assert "Category: meme" in report
    assert "Category: contract" in report
    assert "pump" in report or "signal" in report
    assert "perp" in report or "funding" in report


def test_crypto_symbols_detected(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "BTC ETH SOL PEPE DOGE are pumping")
    report = generate_keyword_report(str(tmp_path))
    assert "BTC" in report
    assert "ETH" in report
    assert "SOL" in report


def test_contract_addresses_detected(tmp_path: Path) -> None:
    addr = "0x1234567890abcdef1234567890abcdef12345678"
    _write_capture(tmp_path, "a.md", f"New token CA: {addr}")
    report = generate_keyword_report(str(tmp_path))
    assert "0x1234567890abcdef" in report


def test_twitter_handles_detected(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "Follow @elonmusk and @VitalikButerin")
    report = generate_keyword_report(str(tmp_path))
    assert "@elonmusk" in report
    assert "@VitalikButerin" in report


def test_existing_keywords_marked(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "btc perp breakout signal")
    kw_file = tmp_path / "keywords.yaml"
    kw_file.write_text(
        "phase_3:\n"
        "  label: Crypto\n"
        "  include: [btc, perp]\n"
        "  exclude: []\n",
        encoding="utf-8",
    )
    report = generate_keyword_report(str(tmp_path), str(kw_file))
    assert "[EXISTING]" in report


def test_cli_subprocess(tmp_path: Path) -> None:
    _write_capture(tmp_path, "cli.md", "PEPE meme coin pump")
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "Keyword Extraction Report" in result.stdout


def test_cli_no_args_shows_usage() -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Usage" in result.stdout
