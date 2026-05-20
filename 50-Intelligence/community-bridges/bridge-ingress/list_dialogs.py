#!/usr/bin/env python3
"""List all Telegram dialogs (chats/groups/channels) for the logged-in account.

Read-only utility: does NOT send messages, write files, or modify any
Telegram state. Used to discover chat_id values for configuring
TG_MEME_CHAT_IDS and TG_CONTRACT_CHAT_IDS.

Usage:
    export TG_API_ID=12345678
    export TG_API_HASH=abcdef1234567890abcdef1234567890
    export TG_SESSION_STRING=<your session string>
    python list_dialogs.py

Output columns:
    TYPE       group / channel / user
    CHAT_ID    integer id (negative for groups/channels)
    TITLE      group/channel title or user display name
    CANDIDATE  yes = suitable for monitoring; no = private user chat

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
    session_string = os.environ.get("TG_SESSION_STRING", "").strip()

    if not api_id_raw or not api_hash or not session_string:
        print("Set TG_API_ID, TG_API_HASH, and TG_SESSION_STRING first.")
        sys.exit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print("ERROR: TG_API_ID must be an integer")
        sys.exit(1)

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    if not client.is_user_authorized():
        print("ERROR: session not authorized. Regenerate via generate_session.py")
        client.disconnect()
        sys.exit(1)

    print("")
    print(f"{'TYPE':<10} {'CHAT_ID':<20} {'CANDIDATE':<10} {'TITLE'}")
    print("-" * 80)

    dialogs = client.get_dialogs()
    for dialog in dialogs:
        entity = dialog.entity
        chat_id = dialog.id
        title = dialog.title or dialog.name or "(unnamed)"

        if dialog.is_group:
            dtype = "group"
            candidate = "yes"
        elif dialog.is_channel:
            dtype = "channel"
            candidate = "yes"
        else:
            dtype = "user"
            candidate = "no"

        print(f"{dtype:<10} {chat_id:<20} {candidate:<10} {title}")

    client.disconnect()

    print("")
    print("-" * 80)
    print("USAGE:")
    print("  Copy the CHAT_ID values for groups/channels you want to monitor.")
    print("  Separate into two categories in your .env:")
    print("")
    print("  TG_MEME_CHAT_IDS=-100xxx,-100yyy")
    print("  TG_CONTRACT_CHAT_IDS=-100zzz,-100www")
    print("")
    print("  meme     = on-chain meme opportunity signal groups")
    print("  contract = crypto contract/perp opportunity signal groups")
    print("")
    print("  A single chat_id must appear in ONLY ONE category.")
    print("  Groups/channels not in either list will be ignored by the listener.")


if __name__ == "__main__":
    main()
