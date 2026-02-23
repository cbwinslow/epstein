#!/usr/bin/env python3
"""Conversation log manager - saves CLI conversation history."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

CONVERSATIONS_DIR = Path(".claude/conversations")


def get_conversation_file():
    """Get today's conversation file path."""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return CONVERSATIONS_DIR / f"{today}.json"


def save_message(role: str, content: str):
    """Save a single message to today's conversation log."""
    filepath = get_conversation_file()
    entry = {"timestamp": datetime.now().isoformat(), "role": role, "content": content}
    with open(filepath, "a") as f:
        f.write(json.dumps(entry) + "\n")


def list_conversations():
    """List all conversation files."""
    if not CONVERSATIONS_DIR.exists():
        print("No conversations saved yet.")
        return
    files = sorted(CONVERSATIONS_DIR.glob("*.json"), reverse=True)
    if not files:
        print("No conversations saved yet.")
        return
    print("Saved conversations:")
    for f in files:
        size = f.stat().st_size
        print(f"  {f.name} ({size} bytes)")


def read_conversation(filename: str):
    """Read a specific conversation file."""
    if not filename.endswith(".json"):
        filename = f"{filename}.json"

    # Try exact match first, then glob match
    filepath = CONVERSATIONS_DIR / filename
    if not filepath.exists():
        # Try partial match
        matches = list(CONVERSATIONS_DIR.glob(f"*{filename}*"))
        if matches:
            filepath = matches[0]
        else:
            print(f"Conversation file not found: {filename}")
            return

    print(f"\n=== {filepath.name} ===\n")
    with open(filepath) as f:
        for line in f:
            entry = json.loads(line)
            role = entry.get("role", "unknown")
            ts = entry.get("timestamp", "")[:19]
            content = entry.get("content", "")[:200]
            print(f"[{ts}] {role}: {content}...")
            print()


def main():
    if len(sys.argv) < 2:
        print("Usage: conversation_log.py <save|list|read> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "save":
        if len(sys.argv) < 3:
            print("Usage: conversation_log.py save <user|assistant> <content>")
            sys.exit(1)
        role = sys.argv[2]
        content = " ".join(sys.argv[3:])
        save_message(role, content)
        print(f"Saved {role} message")

    elif cmd == "list":
        list_conversations()

    elif cmd == "read":
        if len(sys.argv) < 3:
            print("Usage: conversation_log.py read <filename>")
            sys.exit(1)
        read_conversation(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
