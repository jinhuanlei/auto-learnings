#!/usr/bin/env python3
"""Idempotent setup: merge usage-lens hooks into settings.json and create default config."""
import json, os, sys

SETTINGS = os.path.expanduser("~/.claude/settings.json")
CONFIG_DIR = os.path.expanduser("~/.config/usage-lens")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HOOK_BASE = os.path.expanduser("~/.claude/skills/usage-lens/scripts")

NEW_HOOKS = {
    "UserPromptSubmit": [{
        "hooks": [{"type": "command", "command": f"python {HOOK_BASE}/prompt_hook.py"}]
    }],
    "PostToolUse": [{
        "matcher": "Skill",
        "hooks": [{"type": "command", "command": f"python {HOOK_BASE}/post_tool_hook.py"}]
    }],
}

DEFAULT_CONFIG = {
    "verbosity": "standard",
    "log_path": "~/.claude/usage-lens.jsonl",
    "inactive_threshold_days": 30,
    "trend_window_days": 30,
    "cleanup_keep_days": 90,
}

def merge_hooks():
    try:
        with open(SETTINGS) as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    added = []

    for event, entries in NEW_HOOKS.items():
        existing = hooks.get(event, [])
        target_cmd = entries[0]["hooks"][0]["command"]
        if any(
            h.get("command") == target_cmd
            for e in existing for h in e.get("hooks", [])
        ):
            print(f"  already configured: {event}")
        else:
            hooks.setdefault(event, []).extend(entries)
            added.append(event)

    with open(SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)

    if added:
        print(f"  hooks added: {', '.join(added)}")

def create_config():
    if os.path.exists(CONFIG_FILE):
        print(f"  config already exists: {CONFIG_FILE}")
        return
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"  config created: {CONFIG_FILE}")

def check_symlink():
    link = os.path.expanduser("~/.claude/skills/usage-lens")
    if os.path.exists(link) or os.path.islink(link):
        print(f"  symlink exists: {link}")
    else:
        print(f"  WARNING: symlink missing — run:")
        print(f"    ln -s /path/to/boring-skills/skills/usage-lens {link}")

if __name__ == "__main__":
    print("usage-lens setup")
    merge_hooks()
    create_config()
    check_symlink()
    print("done.")
