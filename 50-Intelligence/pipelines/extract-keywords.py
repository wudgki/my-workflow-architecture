#!/usr/bin/env python3
"""Extract candidate keywords from Telegram-Captures for keywords.yaml.

Scans all .md captures, extracts message text, tokenizes, and outputs
frequency-sorted candidate keyword lists grouped by watch_category.
The output helps you decide which terms to add to keywords.yaml to
reduce the null-phase ratio.

Usage (Windows PowerShell):
    python 50-Intelligence\\pipelines\\extract-keywords.py D:\\AI-Workspace\\00-Inbox\\Telegram-Captures\\

Usage (Linux/macOS):
    python3 50-Intelligence/pipelines/extract-keywords.py /data/inbox/Telegram-Captures/

Output:
    - Top tokens by watch_category (meme / contract)
    - Candidate crypto symbols (uppercase 2-6 char tokens)
    - Candidate contract addresses (0x... patterns)
    - Candidate Twitter/X handles (@username patterns)
    - Tokens already covered by current keywords.yaml (for reference)

Requirements: pyyaml

ASCII-only.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import yaml


# --- Patterns ---
_RE_CONTRACT_ADDR = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
_RE_TWITTER_HANDLE = re.compile(r'@[A-Za-z_][A-Za-z0-9_]{1,15}\b')
_RE_CRYPTO_SYMBOL = re.compile(r'\b[A-Z]{2,6}\b')
_RE_WORD = re.compile(r'[a-zA-Z0-9]{2,}')

# Common English stop words to filter out
_STOP_WORDS = frozenset({
    'the', 'be', 'to', 'of', 'and', 'in', 'that', 'have', 'it',
    'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
    'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
    'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
    'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
    'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
    'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first',
    'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
    'give', 'day', 'most', 'us', 'is', 'are', 'was', 'were', 'been',
    'has', 'had', 'did', 'does', 'am', 'may', 'might', 'shall',
    'should', 'must', 'need', 'here', 'very', 'much', 'more', 'still',
    'http', 'https', 'www', 'com', 'org', 'net', 'co',
})


def _parse_frontmatter(filepath: Path) -> Optional[dict[str, Any]]:
    """Extract YAML front-matter from a Markdown file."""
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


def _extract_body(filepath: Path) -> str:
    """Extract message body (after front-matter) from a capture file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return ""

    if not text.startswith("---\n"):
        return text

    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return ""

    body = text[end_idx + 5:]
    # Skip the "# Telegram capture" heading
    if body.startswith("# Telegram capture\n"):
        body = body[len("# Telegram capture\n"):]
    return body.strip()


def _load_existing_keywords(keywords_path: str) -> set[str]:
    """Load all existing keywords from keywords.yaml for comparison."""
    try:
        with open(keywords_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return set()

    existing: set[str] = set()
    for key in data:
        if key.startswith("phase_") or key == "global_exclude":
            block = data[key]
            if isinstance(block, dict):
                for kw in block.get("include", []):
                    existing.add(str(kw).lower())
                for kw in block.get("exclude", []):
                    existing.add(str(kw).lower())
            elif isinstance(block, list):
                for kw in block:
                    existing.add(str(kw).lower())
    return existing


def generate_keyword_report(
    captures_dir: str,
    keywords_yaml_path: str = "",
    top_n: int = 50,
) -> str:
    """Analyze captures and generate candidate keyword report."""
    captures_path = Path(captures_dir)
    if not captures_path.is_dir():
        return f"ERROR: directory not found: {captures_dir}"

    md_files = sorted(captures_path.glob("*.md"))
    if not md_files:
        return f"No .md files found in {captures_dir}"

    # Load existing keywords for comparison
    existing_kw = set()
    if keywords_yaml_path and os.path.exists(keywords_yaml_path):
        existing_kw = _load_existing_keywords(keywords_yaml_path)

    # Categorize captures and extract text
    texts_by_category: dict[str, list[str]] = {
        "meme": [],
        "contract": [],
        "null": [],
    }

    for f in md_files:
        fm = _parse_frontmatter(f)
        body = _extract_body(f)
        if not body:
            continue

        cat = "null"
        if fm:
            cat = fm.get("watch_category") or "null"

        texts_by_category.setdefault(cat, []).append(body)

    # Token extraction per category
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  Keyword Extraction Report")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Captures scanned: {len(md_files)}")
    lines.append(f"Existing keywords loaded: {len(existing_kw)}")
    lines.append("")

    for cat in ["meme", "contract", "null"]:
        texts = texts_by_category.get(cat, [])
        if not texts:
            continue

        all_text = "\n".join(texts)
        all_lower = all_text.lower()

        # Word frequency (lowercased, stop words removed)
        word_counter: Counter = Counter()
        for word in _RE_WORD.findall(all_lower):
            if word not in _STOP_WORDS and len(word) >= 3:
                word_counter[word] += 1

        # Crypto symbols (uppercase 2-6 chars)
        symbol_counter: Counter = Counter()
        for sym in _RE_CRYPTO_SYMBOL.findall(all_text):
            if sym not in ("THE", "AND", "FOR", "NOT", "ARE", "BUT",
                           "ALL", "CAN", "HAS", "HER", "WAS", "ONE",
                           "OUR", "OUT", "YOU", "HAD", "HAS", "HIS",
                           "HOW", "ITS", "MAY", "NEW", "NOW", "OLD",
                           "SEE", "WAY", "WHO", "BOY", "DID", "GET"):
                symbol_counter[sym] += 1

        # Contract addresses
        addresses = _RE_CONTRACT_ADDR.findall(all_text)
        addr_counter: Counter = Counter(addresses)

        # Twitter handles
        handles = _RE_TWITTER_HANDLE.findall(all_text)
        handle_counter: Counter = Counter(handles)

        lines.append("-" * 60)
        lines.append(f"  Category: {cat} ({len(texts)} messages)")
        lines.append("-" * 60)
        lines.append("")

        # Top words
        lines.append(f"  Top {top_n} tokens (frequency):")
        for word, count in word_counter.most_common(top_n):
            marker = " [EXISTING]" if word in existing_kw else ""
            lines.append(f"    {word:<25} {count:>4}{marker}")
        lines.append("")

        # Top symbols
        if symbol_counter:
            lines.append(f"  Candidate crypto symbols (top 30):")
            for sym, count in symbol_counter.most_common(30):
                marker = " [EXISTING]" if sym.lower() in existing_kw else ""
                lines.append(f"    {sym:<10} {count:>4}{marker}")
            lines.append("")

        # Contract addresses
        if addr_counter:
            lines.append(f"  Contract addresses (top 10):")
            for addr, count in addr_counter.most_common(10):
                lines.append(f"    {addr}  x{count}")
            lines.append("")

        # Twitter handles
        if handle_counter:
            lines.append(f"  Twitter/X handles (top 20):")
            for handle, count in handle_counter.most_common(20):
                lines.append(f"    {handle:<20} {count:>4}")
            lines.append("")

    lines.append("=" * 60)
    lines.append("")
    lines.append("NEXT STEPS:")
    lines.append("  1. Review the token lists above")
    lines.append("  2. Pick terms that represent real signals (not noise)")
    lines.append("  3. Add them to 50-Intelligence/pipelines/keywords.yaml:")
    lines.append("     - Meme signals -> phase_3 include (or new phase_5)")
    lines.append("     - Contract signals -> phase_3 include")
    lines.append("     - Noise/spam terms -> global_exclude")
    lines.append("  4. Re-run inbox-stats.py to verify null ratio decreased")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract-keywords.py <captures-directory> [keywords.yaml]")
        print("")
        print("Examples:")
        print("  python extract-keywords.py /data/inbox/Telegram-Captures/")
        print("  python extract-keywords.py D:\\AI-Workspace\\00-Inbox\\Telegram-Captures\\ 50-Intelligence\\pipelines\\keywords.yaml")
        print("  py -3 extract-keywords.py D:\\AI-Workspace\\00-Inbox\\Telegram-Captures\\")
        sys.exit(1)

    captures_dir = sys.argv[1]
    keywords_path = sys.argv[2] if len(sys.argv) >= 3 else ""

    report = generate_keyword_report(captures_dir, keywords_path)
    print(report)


if __name__ == "__main__":
    main()
