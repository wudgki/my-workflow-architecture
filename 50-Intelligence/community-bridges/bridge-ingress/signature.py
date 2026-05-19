"""Telegram webhook secret_token verification.

Telegram does not sign webhook payloads with HMAC. Instead, when you
register a webhook with the optional `secret_token` parameter, Telegram
echoes the raw token back in the X-Telegram-Bot-Api-Secret-Token header
on every request. The bridge compares that header to the configured
secret using a constant-time comparison to defeat timing oracles.

Refs: https://core.telegram.org/bots/api#setwebhook (secret_token field)

ASCII-only.
"""
from __future__ import annotations

import hmac


def verify_telegram_secret(header_value: str | None, expected: str) -> bool:
    """Return True iff the header matches the expected secret.

    Returns False on any of:
      - header missing or empty
      - expected secret empty (defense-in-depth against misconfig)
      - any encoding error

    Uses hmac.compare_digest for constant-time comparison.
    """
    if not header_value or not expected:
        return False
    try:
        return hmac.compare_digest(
            header_value.encode("utf-8"),
            expected.encode("utf-8"),
        )
    except Exception:
        return False
