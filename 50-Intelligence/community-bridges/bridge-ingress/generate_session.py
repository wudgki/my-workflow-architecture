#!/usr/bin/env python3
"""Generate a Telethon StringSession for bridge-ingress.

Run this script ONCE on a machine where you can receive the Telegram
verification code (phone or Telegram app). It will print a session
string that you then store in the TG_SESSION_STRING environment variable
on your VPS.

Usage:
    python generate_session.py

You will be prompted for:
  1. Your phone number (international format, e.g. +8613800138000)
  2. The verification code sent by Telegram
  3. (Optional) Your 2FA password if enabled

The script prints the session string to stdout. Copy it into your
.env file or secrets manager. NEVER commit it to git.

Requirements:
    pip install telethon

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
        print("Set TG_API_ID and TG_API_HASH environment variables first.")
        print("")
        print("  export TG_API_ID=12345678")
        print("  export TG_API_HASH=abcdef1234567890abcdef1234567890")
        print("")
        print("Get them from https://my.telegram.org/apps")
        sys.exit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print("ERROR: TG_API_ID must be an integer")
        sys.exit(1)

    print("=== Telegram Session Generator ===")
    print("")
    print("This will log in to your Telegram account and generate a")
    print("session string. You will need to enter your phone number")
    print("and the verification code Telegram sends you.")
    print("")
    print("The session string gives FULL ACCESS to your account.")
    print("Store it securely. NEVER commit it to git.")
    print("")

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_string = client.session.save()
        print("")
        print("=" * 60)
        print("SESSION STRING (copy this into TG_SESSION_STRING):")
        print("=" * 60)
        print(session_string)
        print("=" * 60)
        print("")
        print("Store this in your .env file on the VPS:")
        print('  TG_SESSION_STRING="' + session_string[:20] + '..."')
        print("")
        print("Done. You can close this terminal.")


if __name__ == "__main__":
    main()
