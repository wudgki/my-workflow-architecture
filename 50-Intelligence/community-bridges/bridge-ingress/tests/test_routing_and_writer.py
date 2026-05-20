"""Phase routing matrix + inbox writer file format & idempotency.

ASCII-only.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from inbox_writer import write_telegram_capture
from phase_router import PhaseRouter


# --------------------------------------------------------------------- #
# phase_router
# --------------------------------------------------------------------- #


@pytest.fixture
def router(keywords_yaml: Path) -> PhaseRouter:
    return PhaseRouter(str(keywords_yaml))


@pytest.mark.parametrize(
    "text, expected",
    [
        ("BTC perp 4h breakout", "phase_3"),
        ("Polymarket election odds shifting", "phase_4"),
        ("Hermes infra status check", "phase_1"),
        ("Jinguan packaging RFP", "phase_2"),
        ("please ignore smoke test", None),    # global_exclude
        ("smoke noise demo", None),            # global_exclude
        ("random foo bar", None),              # no match
        ("BTC paper trade only", None),        # phase_3 exclude wins
        ("", None),                            # empty
    ],
)
def test_route(router: PhaseRouter, text: str, expected: str | None) -> None:
    assert router.route(text) == expected


def test_router_first_match_wins_lowest_phase_first(router: PhaseRouter) -> None:
    # Text mentions both phase_1 (mcp) and phase_3 (btc): phase_1 wins.
    assert router.route("mcp + btc perp combo") == "phase_1"


def test_router_hot_reload_picks_up_new_keywords(tmp_path: Path) -> None:
    p = tmp_path / "keywords.yaml"
    p.write_text(
        "phase_1: {label: a, include: [foo], exclude: []}\n"
        "phase_2: {label: b, include: [], exclude: []}\n"
        "phase_3: {label: c, include: [], exclude: []}\n"
        "phase_4: {label: d, include: [], exclude: []}\n"
        "global_exclude: []\n",
        encoding="utf-8",
    )
    r = PhaseRouter(str(p))
    assert r.route("foo bar") == "phase_1"
    assert r.route("hello bar") is None

    # Bump mtime by a few seconds so detection works regardless of fs
    # timestamp resolution (HFS+ is 1s, ext4 sub-second, NFS varies).
    new_mtime = p.stat().st_mtime + 5
    p.write_text(
        "phase_1: {label: a, include: [], exclude: []}\n"
        "phase_2: {label: b, include: [bar], exclude: []}\n"
        "phase_3: {label: c, include: [], exclude: []}\n"
        "phase_4: {label: d, include: [], exclude: []}\n"
        "global_exclude: []\n",
        encoding="utf-8",
    )
    os.utime(p, (new_mtime, new_mtime))
    reloaded = r.reload_if_changed()
    assert reloaded is True
    assert r.route("foo bar") == "phase_2"
    assert r.route("foo only") is None


def test_router_reload_no_op_when_unchanged(tmp_path: Path) -> None:
    p = tmp_path / "keywords.yaml"
    p.write_text(
        "phase_1: {label: a, include: [foo], exclude: []}\n"
        "phase_2: {label: b, include: [], exclude: []}\n"
        "phase_3: {label: c, include: [], exclude: []}\n"
        "phase_4: {label: d, include: [], exclude: []}\n"
        "global_exclude: []\n",
        encoding="utf-8",
    )
    r = PhaseRouter(str(p))
    assert r.reload_if_changed() is False
    assert r.reload_if_changed() is False


def test_router_missing_file_does_not_raise(tmp_path: Path) -> None:
    r = PhaseRouter(str(tmp_path / "does-not-exist.yaml"))
    assert r.loaded is False
    # Without keywords loaded, every text falls through to None.
    assert r.route("anything BTC perp polymarket") is None


# --------------------------------------------------------------------- #
# inbox_writer
# --------------------------------------------------------------------- #


def _telegram_payload(
    text: str = "",
    chat_id: int = 123,
    message_id: int = 7,
    caption: str | None = None,
) -> dict:
    msg: dict = {
        "message_id": message_id,
        "date": 1_700_000_000,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": 42, "username": "alice"},
    }
    if text:
        msg["text"] = text
    if caption is not None:
        msg["caption"] = caption
    return {"update_id": 999_000 + message_id, "message": msg}


def test_filename_and_frontmatter(router: PhaseRouter, inbox_dir: Path) -> None:
    payload = _telegram_payload(
        "BTC perp signal", chat_id=-100200, message_id=88
    )
    result = write_telegram_capture(
        payload=payload,
        inbox_path=str(inbox_dir),
        phase_router=router,
        bridge_version="0.1.0-test",
    )

    assert result["phase"] == "phase_3"
    assert result["chat_id"] == -100200
    assert result["message_id"] == 88

    file_path = Path(result["file"])
    assert file_path.parent.name == "Telegram-Captures"

    name = file_path.name
    assert name.endswith("_telegram_-100200_88.md")
    # Leading 10 chars must be a YYYY-MM-DD date.
    date_part = name[:10]
    assert date_part[4] == "-" and date_part[7] == "-"
    assert date_part[:4].isdigit()
    assert date_part[5:7].isdigit()
    assert date_part[8:10].isdigit()

    body = file_path.read_text(encoding="utf-8")
    assert body.startswith("---\n")
    front_block = body.split("---", 2)[1]
    fm = yaml.safe_load(front_block)

    assert fm["source"] == "telegram"
    assert fm["source_id"] == "telegram:-100200:88"
    assert fm["chat_id"] == -100200
    assert fm["message_id"] == 88
    assert fm["phase"] == "phase_3"
    assert fm["status"] == "raw"
    assert fm["priority"] == "p2"
    assert fm["owner"] == "intel-summarizer"
    assert fm["bridge_version"] == "0.1.0-test"
    assert fm["from_username"] == "alice"
    assert "BTC perp signal" in body


def test_idempotent_redelivery(router: PhaseRouter, inbox_dir: Path) -> None:
    payload = _telegram_payload(
        "Polymarket election", chat_id=1, message_id=2
    )
    r1 = write_telegram_capture(payload, str(inbox_dir), router, "0.1.0-test")
    r2 = write_telegram_capture(payload, str(inbox_dir), router, "0.1.0-test")
    assert r1["file"] == r2["file"]
    captures = list((inbox_dir / "Telegram-Captures").iterdir())
    assert len(captures) == 1


def test_global_exclude_routes_to_null(
    router: PhaseRouter, inbox_dir: Path
) -> None:
    payload = _telegram_payload(
        "please ignore noise", chat_id=5, message_id=6
    )
    result = write_telegram_capture(
        payload, str(inbox_dir), router, "0.1.0-test"
    )
    assert result["phase"] is None
    body = Path(result["file"]).read_text(encoding="utf-8")
    fm = yaml.safe_load(body.split("---", 2)[1])
    # YAML dumps None as 'null' on the wire; safe_load brings it back as None.
    assert fm["phase"] is None


def test_no_message_field_raises(
    router: PhaseRouter, inbox_dir: Path
) -> None:
    payload = {"update_id": 1}
    with pytest.raises(ValueError):
        write_telegram_capture(payload, str(inbox_dir), router, "0.1.0-test")


def test_caption_used_when_no_text(
    router: PhaseRouter, inbox_dir: Path
) -> None:
    payload = _telegram_payload(
        text="",
        chat_id=7,
        message_id=100,
        caption="Jinguan packaging factory tour photos",
    )
    result = write_telegram_capture(
        payload, str(inbox_dir), router, "0.1.0-test"
    )
    assert result["phase"] == "phase_2"


def test_missing_chat_id_raises(
    router: PhaseRouter, inbox_dir: Path
) -> None:
    payload = {
        "update_id": 1,
        "message": {"message_id": 1, "date": 0, "text": "hi"},
    }
    with pytest.raises(ValueError):
        write_telegram_capture(payload, str(inbox_dir), router, "0.1.0-test")
