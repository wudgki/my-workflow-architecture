#!/usr/bin/env python3
"""Generate a Telethon StringSession for bridge-ingress.

Run this script ONCE on a machine where you can receive the Telegram
verification code. It will print a session string to store in
TG_SESSION_STRING on your VPS.

Usage:
    export TG_API_ID=12345678
    export TG_API_HASH=abcdef1234567890abcdef1234567890
    python generate_session.py

Requirements: pip install telethon

ASCII-only.
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("ERROR: telethon not installed. Run: pip install telethon")
        sys.exit(1)

    api_id_raw = os.environ.get("TG_API_ID", "").strip()
    api_hash = os.environ.get("TG_API_HASH", "").strip()

    if not api_id_raw or not api_hash:
        print("Set TG_API_ID and TG_API_HASH first.")
        print("  export TG_API_ID=12345678")
        print("  export TG_API_HASH=abcdef...")
        print("Get them from https://my.telegram.org/apps")
        sys.exit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print("ERROR: TG_API_ID must be an integer")
        sys.exit(1)

    print("=== Telegram Session Generator ===")
    print("Session string = full login credential. NEVER commit to git.")
    print("")

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_string = client.session.save()
        print("=" * 60)
        print("SESSION STRING:")
        print("=" * 60)
        print(session_string)
        print("=" * 60)
        print("Store in .env: TG_SESSION_STRING=<above>")


if __name__ == "__main__":
    main()
