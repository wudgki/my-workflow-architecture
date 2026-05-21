"""Unit tests for extract-keywords.py.

Tests n-gram extraction, CSV/MD output, existing keyword marking,
null-phase prioritization, and CLI subprocess invocation.

ASCII-only.
"""
from __future__ import annotations

import csv
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

extract_candidates = _MOD.extract_candidates
_generate_csv = _MOD._generate_csv
_generate_markdown = _MOD._generate_markdown
_tokenize = _MOD._tokenize
_extract_ngrams = _MOD._extract_ngrams


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #


def _write_capture(
    tmp_path: Path,
    filename: str,
    text: str = "BTC pump signal",
    watch_category: str = "meme",
    phase: str = "null",
    chat_id: int = -100111,
) -> None:
    content = (
        "---\n"
        "captured_at: 2026-05-20T03:14:15+00:00\n"
        "source: telegram\n"
        f"chat_id: {chat_id}\n"
        "message_id: 1\n"
        f"phase: {phase}\n"
        f"watch_category: {watch_category}\n"
        "status: raw\n"
        "---\n"
        "\n"
        "# Telegram capture\n"
        "\n"
        f"{text}\n"
    )
    (tmp_path / filename).write_text(content, encoding="utf-8")


# --------------------------------------------------------------------- #
# Tests: n-gram extraction
# --------------------------------------------------------------------- #


def test_tokenize_removes_stop_words() -> None:
    tokens = _tokenize("the quick BTC pump signal")
    assert "the" not in tokens
    assert "quick" in tokens
    assert "btc" in tokens
    assert "pump" in tokens


def test_unigrams() -> None:
    tokens = _tokenize("btc pump moon lambo")
    grams = _extract_ngrams(tokens, 1)
    assert "btc" in grams
    assert "pump" in grams


def test_bigrams() -> None:
    tokens = _tokenize("btc pump moon lambo")
    grams = _extract_ngrams(tokens, 2)
    assert "btc pump" in grams
    assert "pump moon" in grams


def test_trigrams() -> None:
    tokens = _tokenize("btc pump moon lambo signal")
    grams = _extract_ngrams(tokens, 3)
    assert "btc pump moon" in grams


def test_quadgrams() -> None:
    tokens = _tokenize("btc pump moon lambo signal")
    grams = _extract_ngrams(tokens, 4)
    assert "btc pump moon lambo" in grams


def test_ngrams_short_text() -> None:
    tokens = _tokenize("btc")
    assert _extract_ngrams(tokens, 2) == []
    assert _extract_ngrams(tokens, 3) == []


# --------------------------------------------------------------------- #
# Tests: candidate extraction
# --------------------------------------------------------------------- #


def test_basic_extraction(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "BTC pump BTC pump BTC")
    _write_capture(tmp_path, "b.md", "ETH perp funding rate")
    candidates = extract_candidates(str(tmp_path), min_count=1)
    texts = [c.text for c in candidates]
    assert any("btc" in t for t in texts)


def test_null_phase_prioritized(tmp_path: Path) -> None:
    # 3 captures with null phase mentioning "doge"
    for i in range(3):
        _write_capture(tmp_path, f"null_{i}.md", "DOGE meme pump",
                       phase="null")
    # 1 capture with phase_3 mentioning "eth"
    _write_capture(tmp_path, "hit.md", "ETH perp breakout",
                   phase="phase_3")
    candidates = extract_candidates(str(tmp_path), min_count=1)
    # "doge" should rank higher (100% null-phase)
    doge_idx = next((i for i, c in enumerate(candidates) if "doge" in c.text), 999)
    eth_idx = next((i for i, c in enumerate(candidates) if "eth" in c.text), 999)
    assert doge_idx < eth_idx


def test_existing_keywords_marked(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "btc perp breakout signal btc perp")
    kw_file = tmp_path / "keywords.yaml"
    kw_file.write_text(
        "phase_3:\n"
        "  label: Crypto\n"
        "  include: [btc, perp]\n"
        "  exclude: []\n",
        encoding="utf-8",
    )
    candidates = extract_candidates(str(tmp_path), str(kw_file), min_count=1)
    btc_cand = next((c for c in candidates if c.text == "btc"), None)
    assert btc_cand is not None
    assert btc_cand.existing is True


def test_candidate_fields(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "SOL pump SOL pump SOL",
                   watch_category="meme", chat_id=-100111, phase="null")
    _write_capture(tmp_path, "b.md", "SOL breakout",
                   watch_category="contract", chat_id=-100222, phase="null")
    candidates = extract_candidates(str(tmp_path), min_count=1)
    sol = next((c for c in candidates if c.text == "SOL"), None)
    assert sol is not None
    assert sol.candidate_type == "symbol"
    assert sol.frequency >= 4
    assert sol.document_frequency == 2
    assert len(sol.chat_ids) == 2
    assert "meme" in sol.watch_categories
    assert "contract" in sol.watch_categories


# --------------------------------------------------------------------- #
# Tests: CSV output
# --------------------------------------------------------------------- #


def test_csv_output(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "PEPE meme pump PEPE")
    candidates = extract_candidates(str(tmp_path), min_count=1)
    csv_path = tmp_path / "out" / "keyword-candidates.csv"
    _generate_csv(candidates, csv_path)
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    assert "candidate" in rows[0]
    assert "candidate_type" in rows[0]
    assert "frequency" in rows[0]
    assert "null_phase_ratio" in rows[0]
    assert "existing" in rows[0]


# --------------------------------------------------------------------- #
# Tests: Markdown output
# --------------------------------------------------------------------- #


def test_markdown_output(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", "DOGE pump signal DOGE pump")
    candidates = extract_candidates(str(tmp_path), min_count=1)
    md_path = tmp_path / "out" / "keyword-candidates.md"
    _generate_markdown(candidates, md_path, str(tmp_path), top_n=50)
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "# Keyword Candidates Report" in content
    assert "candidate" in content
    assert "Next Steps" in content


# --------------------------------------------------------------------- #
# Tests: CLI subprocess
# --------------------------------------------------------------------- #


def test_cli_basic(tmp_path: Path) -> None:
    _write_capture(tmp_path, "cli.md", "BTC pump moon BTC pump")
    out_dir = tmp_path / "reports"
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), str(tmp_path),
         "--output-dir", str(out_dir), "--min-count", "1"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "Extracted" in result.stdout
    assert (out_dir / "keyword-candidates.csv").exists()
    assert (out_dir / "keyword-candidates.md").exists()


def test_cli_no_args_shows_error() -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0


def test_cli_empty_dir(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), str(tmp_path),
         "--output-dir", str(tmp_path / "out")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "No candidates" in result.stdout
