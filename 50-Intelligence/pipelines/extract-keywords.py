#!/usr/bin/env python3
"""Extract candidate keywords from Telegram-Captures for keywords.yaml.

Scans all .md captures, extracts message text, generates n-grams (1-4),
and outputs frequency-sorted candidate keyword reports grouped by
watch_category. Prioritizes candidates from null-phase captures.

Usage (Linux/macOS):
    python3 extract-keywords.py /data/inbox/Telegram-Captures/

Usage (Windows PowerShell):
    py -3 extract-keywords.py D:\\AI-Workspace\\00-Inbox\\Telegram-Captures\\
    py -3 extract-keywords.py D:\\AI-Workspace\\00-Inbox\\Telegram-Captures\\ --keywords 50-Intelligence\\pipelines\\keywords.yaml

Options:
    --keywords PATH    Path to existing keywords.yaml (marks existing terms)
    --min-count N      Minimum frequency to include (default: 2)
    --top-n N          Max candidates per category (default: 100)
    --by-chat          Include per-chat_id breakdown
    --output-dir DIR   Output directory (default: 50-Intelligence/pipelines/reports/)

Output files:
    <output-dir>/keyword-candidates.md   Human-readable report
    <output-dir>/keyword-candidates.csv  Machine-readable table

Requirements: pyyaml
ASCII-only.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# --- Patterns ---
_RE_CONTRACT_ADDR = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
_RE_TWITTER_HANDLE = re.compile(r'@[A-Za-z_][A-Za-z0-9_]{1,15}\b')
_RE_CRYPTO_SYMBOL = re.compile(r'\b[A-Z]{2,6}\b')
_RE_WORD = re.compile(r'[a-zA-Z0-9]+')

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
    'http', 'https', 'www', 'com', 'org', 'net', 'co', 'io',
    'telegram', 'capture',
})

_SYMBOL_EXCLUDE = frozenset({
    'THE', 'AND', 'FOR', 'NOT', 'ARE', 'BUT', 'ALL', 'CAN', 'HAS',
    'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'YOU', 'HAD', 'HIS', 'HOW',
    'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'WAY', 'WHO', 'DID',
    'GET', 'CMD', 'INFO', 'WARN',
})


@dataclass
class CaptureRecord:
    filename: str
    chat_id: str
    watch_category: str
    phase: str
    body: str


@dataclass
class Candidate:
    text: str
    candidate_type: str  # unigram, bigram, trigram, quadgram, symbol, address, handle
    frequency: int = 0
    document_frequency: int = 0
    chat_ids: set = field(default_factory=set)
    watch_categories: set = field(default_factory=set)
    null_phase_count: int = 0
    total_count: int = 0
    example_filename: str = ""
    existing: bool = False


# --- Parsing ---

def _parse_frontmatter(filepath: Path) -> Optional[dict[str, Any]]:
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
    if body.startswith("# Telegram capture\n"):
        body = body[len("# Telegram capture\n"):]
    return body.strip()


def _load_existing_keywords(keywords_path: str) -> set[str]:
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


# --- N-gram extraction ---

def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, filtering stop words."""
    words = _RE_WORD.findall(text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) >= 2]


def _extract_ngrams(tokens: list[str], n: int) -> list[str]:
    """Extract n-grams from token list."""
    if len(tokens) < n:
        return []
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


# --- Main logic ---

def extract_candidates(
    captures_dir: str,
    keywords_path: str = "",
    min_count: int = 2,
    top_n: int = 100,
) -> list[Candidate]:
    """Extract candidate keywords from captures directory."""
    captures_path = Path(captures_dir)
    if not captures_path.is_dir():
        return []

    md_files = sorted(captures_path.glob("*.md"))
    if not md_files:
        return []

    existing_kw = set()
    if keywords_path and os.path.exists(keywords_path):
        existing_kw = _load_existing_keywords(keywords_path)

    # Parse all captures
    records: list[CaptureRecord] = []
    for f in md_files:
        fm = _parse_frontmatter(f)
        body = _extract_body(f)
        if not body:
            continue
        chat_id = str(fm.get("chat_id", "unknown")) if fm else "unknown"
        watch_cat = (fm.get("watch_category") or "null") if fm else "null"
        phase = str(fm.get("phase") or "null") if fm else "null"
        records.append(CaptureRecord(
            filename=f.name,
            chat_id=chat_id,
            watch_category=watch_cat,
            phase=phase,
            body=body,
        ))

    # Accumulate candidates
    candidate_map: dict[str, Candidate] = {}

    for rec in records:
        tokens = _tokenize(rec.body)
        is_null_phase = rec.phase == "null" or rec.phase == "None"

        doc_seen: set[str] = set()

        # --- Crypto symbols FIRST (preserves uppercase canonical form) ---
        # Use "symbol:" prefix in the key to avoid collision with
        # lowercase n-gram keys (e.g. "sol" unigram vs "SOL" symbol).
        for sym in _RE_CRYPTO_SYMBOL.findall(rec.body):
            if sym in _SYMBOL_EXCLUDE:
                continue
            key = "symbol:" + sym
            if key not in candidate_map:
                candidate_map[key] = Candidate(
                    text=sym, candidate_type="symbol",
                )
            c = candidate_map[key]
            c.frequency += 1
            c.total_count += 1
            c.chat_ids.add(rec.chat_id)
            c.watch_categories.add(rec.watch_category)
            if is_null_phase:
                c.null_phase_count += 1
            if not c.example_filename:
                c.example_filename = rec.filename
            if key not in doc_seen:
                c.document_frequency += 1
                doc_seen.add(key)

        # --- N-grams (lowercase) ---
        ngram_types = [
            (1, "unigram"),
            (2, "bigram"),
            (3, "trigram"),
            (4, "quadgram"),
        ]

        for n, ctype in ngram_types:
            grams = _extract_ngrams(tokens, n)
            for gram in grams:
                key = "ngram:" + gram
                if key not in candidate_map:
                    candidate_map[key] = Candidate(
                        text=gram,
                        candidate_type=ctype,
                    )
                c = candidate_map[key]
                c.frequency += 1
                c.total_count += 1
                c.chat_ids.add(rec.chat_id)
                c.watch_categories.add(rec.watch_category)
                if is_null_phase:
                    c.null_phase_count += 1
                if not c.example_filename:
                    c.example_filename = rec.filename
                if key not in doc_seen:
                    c.document_frequency += 1
                    doc_seen.add(key)

        # Contract addresses
        for addr in _RE_CONTRACT_ADDR.findall(rec.body):
            key = "addr:" + addr.lower()
            if key not in candidate_map:
                candidate_map[key] = Candidate(
                    text=addr, candidate_type="address",
                )
            c = candidate_map[key]
            c.frequency += 1
            c.chat_ids.add(rec.chat_id)
            c.watch_categories.add(rec.watch_category)
            if is_null_phase:
                c.null_phase_count += 1
            if not c.example_filename:
                c.example_filename = rec.filename
            if key not in doc_seen:
                c.document_frequency += 1
                doc_seen.add(key)

        # Twitter handles
        for handle in _RE_TWITTER_HANDLE.findall(rec.body):
            key = "handle:" + handle.lower()
            if key not in candidate_map:
                candidate_map[key] = Candidate(
                    text=handle, candidate_type="handle",
                )
            c = candidate_map[key]
            c.frequency += 1
            c.chat_ids.add(rec.chat_id)
            c.watch_categories.add(rec.watch_category)
            if is_null_phase:
                c.null_phase_count += 1
            if not c.example_filename:
                c.example_filename = rec.filename
            if key not in doc_seen:
                c.document_frequency += 1
                doc_seen.add(key)

    # Mark existing
    for key, c in candidate_map.items():
        if c.text.lower() in existing_kw:
            c.existing = True

    # Filter and sort: prioritize null-phase candidates, then by frequency
    candidates = [c for c in candidate_map.values() if c.frequency >= min_count]
    candidates.sort(key=lambda c: (-(c.null_phase_count / max(c.total_count, 1)), -c.frequency))

    return candidates[:top_n * 5]  # return more, let caller slice per category


# --- Output generation ---

def _generate_csv(candidates: list[Candidate], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "candidate", "candidate_type", "frequency",
            "document_frequency", "chat_id_coverage",
            "watch_category_coverage", "null_phase_ratio",
            "example_filename", "existing",
        ])
        for c in candidates:
            null_ratio = f"{c.null_phase_count / max(c.total_count, 1):.2f}"
            writer.writerow([
                c.text,
                c.candidate_type,
                c.frequency,
                c.document_frequency,
                len(c.chat_ids),
                ",".join(sorted(c.watch_categories)),
                null_ratio,
                c.example_filename,
                c.existing,
            ])


def _generate_markdown(candidates: list[Candidate], output_path: Path,
                       captures_dir: str, top_n: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Keyword Candidates Report")
    lines.append("")
    lines.append(f"Source: `{captures_dir}`")
    lines.append(f"Total candidates (after min-count filter): {len(candidates)}")
    lines.append("")
    lines.append("Sorted by: null-phase ratio (desc), then frequency (desc)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by type
    by_type: dict[str, list[Candidate]] = defaultdict(list)
    for c in candidates:
        by_type[c.candidate_type].append(c)

    type_order = ["unigram", "bigram", "trigram", "quadgram",
                  "symbol", "address", "handle"]

    for ctype in type_order:
        items = by_type.get(ctype, [])
        if not items:
            continue
        lines.append(f"## {ctype.title()} ({len(items)} candidates)")
        lines.append("")
        lines.append("| candidate | freq | doc_freq | chats | categories | null% | existing | example |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for c in items[:top_n]:
            null_pct = f"{c.null_phase_count * 100 / max(c.total_count, 1):.0f}%"
            cats = ",".join(sorted(c.watch_categories))
            existing_mark = "YES" if c.existing else ""
            lines.append(
                f"| {c.text} | {c.frequency} | {c.document_frequency} "
                f"| {len(c.chat_ids)} | {cats} | {null_pct} "
                f"| {existing_mark} | {c.example_filename} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    lines.append("1. Review candidates with high null-phase ratio (these are signals currently unrouted)")
    lines.append("2. Pick terms that represent real trading/meme signals")
    lines.append("3. Add to keywords.yaml (phase_3 for contract, phase_5 for meme, or global_exclude for noise)")
    lines.append("4. Re-run inbox-stats.py to verify null ratio decreased")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# --- CLI ---

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract candidate keywords from Telegram-Captures",
    )
    parser.add_argument("captures_dir", help="Path to Telegram-Captures directory")
    parser.add_argument("--keywords", default="", help="Path to existing keywords.yaml")
    parser.add_argument("--min-count", type=int, default=2, help="Min frequency (default: 2)")
    parser.add_argument("--top-n", type=int, default=100, help="Max candidates per type (default: 100)")
    parser.add_argument("--by-chat", action="store_true", help="Include per-chat breakdown")
    parser.add_argument("--output-dir", default="", help="Output directory for reports")

    args = parser.parse_args()

    captures_dir = args.captures_dir
    if not Path(captures_dir).is_dir():
        print(f"ERROR: directory not found: {captures_dir}")
        sys.exit(1)

    # Determine output dir
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Default: 50-Intelligence/pipelines/reports/ relative to script
        script_dir = Path(__file__).resolve().parent
        output_dir = script_dir / "reports"

    candidates = extract_candidates(
        captures_dir=captures_dir,
        keywords_path=args.keywords,
        min_count=args.min_count,
        top_n=args.top_n,
    )

    if not candidates:
        print("No candidates found (empty directory or all below min-count).")
        sys.exit(0)

    # Generate outputs
    csv_path = output_dir / "keyword-candidates.csv"
    md_path = output_dir / "keyword-candidates.md"

    _generate_csv(candidates, csv_path)
    _generate_markdown(candidates, md_path, captures_dir, args.top_n)

    # Also print summary to stdout
    print(f"Extracted {len(candidates)} candidates")
    print(f"  CSV: {csv_path}")
    print(f"  MD:  {md_path}")
    print("")
    print("Top 20 candidates (by null-phase priority):")
    for c in candidates[:20]:
        null_pct = f"{c.null_phase_count * 100 / max(c.total_count, 1):.0f}%"
        mark = " [EXISTING]" if c.existing else ""
        print(f"  {c.text:<30} freq={c.frequency:<4} null={null_pct:<5} type={c.candidate_type}{mark}")


if __name__ == "__main__":
    main()
