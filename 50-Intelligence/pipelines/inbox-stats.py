#!/usr/bin/env python3
"""Inbox health statistics for Telegram-Captures.

Scans all .md files in a captures directory, parses YAML front-matter,
and prints a summary report including:
  - Total captures (date range)
  - Breakdown by watch_category (meme / contract / null)
  - Breakdown by phase (phase_1..phase_4 / null)
  - Breakdown by chat_id
  - Hourly distribution (last 24h)
  - Null-phase ratio (indicator for keywords.yaml coverage)

Usage:
    python inbox-stats.py /data/inbox/Telegram-Captures/
    python inbox-stats.py D:\\AI-Workspace\\00-Inbox\\Telegram-Captures\\

Requirements: pyyaml (same as bridge-ingress)

ASCII-only.
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


def _parse_frontmatter(filepath: Path) -> Optional[dict[str, Any]]:
    """Extract YAML front-matter from a Markdown file.

    Returns None if the file has no valid front-matter block.
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    if not text.startswith("---\n"):
        return None

    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return None

    yaml_block = text[4:end_idx]
    try:
        data = yaml.safe_load(yaml_block)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def _format_bar(count: int, max_count: int, width: int = 30) -> str:
    """Create a simple ASCII bar chart segment."""
    if max_count == 0:
        return ""
    bar_len = int((count / max_count) * width)
    return "#" * bar_len


def _format_pct(count: int, total: int) -> str:
    """Format as percentage string."""
    if total == 0:
        return "0%"
    return f"{count * 100 / total:.1f}%"


def generate_report(captures_dir: str) -> str:
    """Scan captures directory and generate statistics report.

    Returns the report as a multi-line string.
    """
    captures_path = Path(captures_dir)
    if not captures_path.is_dir():
        return f"ERROR: directory not found: {captures_dir}"

    md_files = sorted(captures_path.glob("*.md"))
    if not md_files:
        return f"No .md files found in {captures_dir}"

    # Parse all front-matters
    records: list[dict[str, Any]] = []
    parse_errors = 0
    for f in md_files:
        fm = _parse_frontmatter(f)
        if fm is not None:
            fm["_filename"] = f.name
            records.append(fm)
        else:
            parse_errors += 1

    total = len(records)
    if total == 0:
        return f"0 parseable captures in {captures_dir} ({parse_errors} parse errors)"

    # Date range from captured_at field
    dates: list[str] = []
    for r in records:
        ca = r.get("captured_at", "")
        if isinstance(ca, str) and len(ca) >= 10:
            dates.append(ca[:10])
        elif hasattr(ca, "isoformat"):
            dates.append(str(ca)[:10])
    date_min = min(dates) if dates else "?"
    date_max = max(dates) if dates else "?"

    # Counters
    category_counter: Counter = Counter()
    phase_counter: Counter = Counter()
    chat_counter: Counter = Counter()
    hour_counter: Counter = Counter()

    for r in records:
        cat = r.get("watch_category") or "null"
        category_counter[cat] += 1

        phase = r.get("phase") or "null"
        phase_counter[str(phase)] += 1

        chat_id = r.get("chat_id")
        if chat_id is not None:
            chat_counter[str(chat_id)] += 1

        ca = r.get("captured_at", "")
        if isinstance(ca, str) and len(ca) >= 13:
            try:
                hour = int(ca[11:13])
                hour_counter[hour] += 1
            except ValueError:
                pass

    # Build report
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"  Inbox Stats: {date_min} to {date_max}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total captures: {total}")
    if parse_errors:
        lines.append(f"Parse errors (skipped): {parse_errors}")
    lines.append("")

    # By watch_category
    lines.append("By watch_category:")
    for cat in ["meme", "contract", "null"]:
        c = category_counter.get(cat, 0)
        lines.append(f"  {cat:<12} {c:>6}  ({_format_pct(c, total)})")
    lines.append("")

    # By phase
    lines.append("By phase:")
    for p in ["phase_1", "phase_2", "phase_3", "phase_4", "null"]:
        c = phase_counter.get(p, 0)
        marker = " <-- keywords gap?" if p == "null" and c > total * 0.5 else ""
        lines.append(f"  {p:<12} {c:>6}  ({_format_pct(c, total)}){marker}")
    null_ratio = phase_counter.get("null", 0) / total if total else 0
    lines.append(f"  null ratio: {null_ratio:.1%}")
    if null_ratio > 0.4:
        lines.append("  WARNING: high null ratio - consider expanding keywords.yaml")
    lines.append("")

    # By chat_id (top 10)
    lines.append("By chat_id (top 10):")
    for chat_id, c in chat_counter.most_common(10):
        lines.append(f"  {chat_id:<22} {c:>6}  ({_format_pct(c, total)})")
    lines.append("")

    # Hourly distribution (0-23)
    lines.append("Hourly distribution (UTC):")
    max_hour = max(hour_counter.values()) if hour_counter else 1
    for h in range(24):
        c = hour_counter.get(h, 0)
        bar = _format_bar(c, max_hour, width=20)
        lines.append(f"  {h:02d}:00  {bar:<20} {c}")
    lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python inbox-stats.py <captures-directory>")
        print("")
        print("Example:")
        print("  python inbox-stats.py /data/inbox/Telegram-Captures/")
        sys.exit(1)

    captures_dir = sys.argv[1]
    report = generate_report(captures_dir)
    print(report)


if __name__ == "__main__":
    main()
