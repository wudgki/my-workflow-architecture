"""Telegram secret_token verification.

ASCII-only.
"""
from __future__ import annotations

from signature import verify_telegram_secret


def test_correct_secret_matches(fake_secret: str) -> None:
    assert verify_telegram_secret(fake_secret, fake_secret) is True


def test_wrong_secret_rejected(fake_secret: str) -> None:
    assert verify_telegram_secret("wrong-value", fake_secret) is False


def test_missing_header_rejected(fake_secret: str) -> None:
    assert verify_telegram_secret(None, fake_secret) is False


def test_empty_header_rejected(fake_secret: str) -> None:
    assert verify_telegram_secret("", fake_secret) is False


def test_empty_expected_rejected() -> None:
    # Defense against misconfiguration: if the operator forgets to set
    # the env var, the bridge should reject ALL traffic, not match-all.
    assert verify_telegram_secret("anything", "") is False


def test_case_sensitive(fake_secret: str) -> None:
    # secret_token comparison is byte-exact, never normalized.
    assert verify_telegram_secret(fake_secret.upper(), fake_secret) is False


def test_unicode_header_does_not_crash(fake_secret: str) -> None:
    # If a misbehaving client sends non-ASCII bytes in the header, we
    # should reject it cleanly rather than raise.
    assert verify_telegram_secret("\u4e2d\u6587", fake_secret) is False
