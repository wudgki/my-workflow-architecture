"""Unit tests for inbox-stats.py.

Tests front-matter parsing, report generation, and edge cases.
Uses temp directories with fake .md captures. No real data needed.

ASCII-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add pipelines/ to sys.path so we can import inbox_stats as a module.
_PIPELINES_DIR = Path(__file__).resolve().parent.parent
if str(_PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINES_DIR))

# Import after path manipulation (inbox-stats.py has a hyphen in the
# filename convention but module uses underscore; we use importlib).
import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "inbox_stats", str(_PIPELINES_DIR / "inbox-stats.py")
)
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MOD
_SPEC.loader.exec_module(_MOD)

_parse_frontmatter = _MOD._parse_frontmatter
generate_report = _MOD.generate_report


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #


def _write_capture(
    tmp_path: Path,
    filename: str,
    phase: str = "phase_3",
    watch_category: str = "meme",
    chat_id: int = -100111,
    message_id: int = 1,
    captured_at: str = "2026-05-20T03:14:15+00:00",
) -> Path:
    """Create a fake capture .md file with valid front-matter."""
    content = (
        "---\n"
        f"captured_at: {captured_at}\n"
        f"source: telegram\n"
        f"chat_id: {chat_id}\n"
        f"message_id: {message_id}\n"
        f"phase: {phase}\n"
        f"watch_category: {watch_category}\n"
        f"status: raw\n"
        "---\n"
        "\n"
        "# Test capture\n"
        "\n"
        "Hello world\n"
    )
    filepath = tmp_path / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


# --------------------------------------------------------------------- #
# Tests: _parse_frontmatter
# --------------------------------------------------------------------- #


def test_parse_valid_frontmatter(tmp_path: Path) -> None:
    f = _write_capture(tmp_path, "test.md", phase="phase_3")
    fm = _parse_frontmatter(f)
    assert fm is not None
    assert fm["phase"] == "phase_3"
    assert fm["chat_id"] == -100111
    assert fm["source"] == "telegram"


def test_parse_no_frontmatter(tmp_path: Path) -> None:
    f = tmp_path / "no_fm.md"
    f.write_text("# Just a heading\n\nNo front-matter here.\n")
    assert _parse_frontmatter(f) is None


def test_parse_broken_yaml(tmp_path: Path) -> None:
    f = tmp_path / "broken.md"
    f.write_text("---\n[invalid yaml\n---\n\nbody\n")
    assert _parse_frontmatter(f) is None


def test_parse_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "empty.md"
    f.write_text("")
    assert _parse_frontmatter(f) is None


# --------------------------------------------------------------------- #
# Tests: generate_report
# --------------------------------------------------------------------- #


def test_report_empty_dir(tmp_path: Path) -> None:
    report = generate_report(str(tmp_path))
    assert "No .md files" in report


def test_report_nonexistent_dir() -> None:
    report = generate_report("/nonexistent/path/xyz")
    assert "ERROR" in report


def test_report_basic(tmp_path: Path) -> None:
    _write_capture(tmp_path, "a.md", phase="phase_3",
                   watch_category="meme", chat_id=-100111)
    _write_capture(tmp_path, "b.md", phase="phase_4",
                   watch_category="contract", chat_id=-100222)
    _write_capture(tmp_path, "c.md", phase="null",
                   watch_category="contract", chat_id=-100222)

    report = generate_report(str(tmp_path))
    assert "Total captures: 3" in report
    assert "meme" in report
    assert "contract" in report
    assert "phase_3" in report
    assert "phase_4" in report
    assert "null" in report
    assert "-100111" in report
    assert "-100222" in report


def test_report_high_null_ratio_warning(tmp_path: Path) -> None:
    # Create 10 captures, 8 with null phase -> 80% null -> warning
    for i in range(8):
        _write_capture(tmp_path, f"null_{i}.md", phase="null",
                       message_id=i)
    for i in range(2):
        _write_capture(tmp_path, f"hit_{i}.md", phase="phase_3",
                       message_id=100 + i)

    report = generate_report(str(tmp_path))
    assert "WARNING" in report
    assert "keywords.yaml" in report


def test_report_no_warning_when_coverage_good(tmp_path: Path) -> None:
    # Create 10 captures, only 2 null -> 20% -> no warning
    for i in range(8):
        _write_capture(tmp_path, f"hit_{i}.md", phase="phase_3",
                       message_id=i)
    for i in range(2):
        _write_capture(tmp_path, f"null_{i}.md", phase="null",
                       message_id=100 + i)

    report = generate_report(str(tmp_path))
    assert "WARNING" not in report


def test_report_hourly_distribution(tmp_path: Path) -> None:
    _write_capture(tmp_path, "morning.md",
                   captured_at="2026-05-20T08:30:00+00:00",
                   message_id=1)
    _write_capture(tmp_path, "evening.md",
                   captured_at="2026-05-20T20:15:00+00:00",
                   message_id=2)

    report = generate_report(str(tmp_path))
    assert "08:00" in report
    assert "20:00" in report


def test_report_parse_errors_noted(tmp_path: Path) -> None:
    # One valid, one broken
    _write_capture(tmp_path, "good.md", phase="phase_1")
    broken = tmp_path / "bad.md"
    broken.write_text("---\n[invalid\n---\nbody\n")

    report = generate_report(str(tmp_path))
    assert "Total captures: 1" in report
    assert "Parse errors" in report



# --------------------------------------------------------------------- #
# Tests: CLI subprocess invocation
# --------------------------------------------------------------------- #

import subprocess


_SCRIPT_PATH = _PIPELINES_DIR / "inbox-stats.py"


def test_cli_with_valid_captures(tmp_path: Path) -> None:
    """Run inbox-stats.py as a subprocess with sys.executable."""
    _write_capture(tmp_path, "cli_test.md", phase="phase_3",
                   watch_category="meme", chat_id=-100111)
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "Total captures: 1" in result.stdout
    assert "phase_3" in result.stdout


def test_cli_with_empty_dir(tmp_path: Path) -> None:
    """Empty dir should produce 'No .md files' and exit 0."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "No .md files" in result.stdout


def test_cli_no_args_shows_usage() -> None:
    """No arguments should show usage and exit 1."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Usage" in result.stdout or "usage" in result.stdout.lower()
