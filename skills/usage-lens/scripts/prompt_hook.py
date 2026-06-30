#!/usr/bin/env python3
"""UserPromptSubmit hook — writes user prompt to /tmp for trigger detection."""
import sys, os, json

try:
    data = json.load(sys.stdin)
    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")
    with open(f"/tmp/claude-usage-lens-{session_id}.txt", "w") as f:
        f.write(prompt)
except Exception as e:
    try:
        with open(os.path.expanduser("~/.claude/usage-lens-errors.log"), "a") as f:
            f.write(f"prompt_hook: {e}\n")
    except Exception:
        pass

sys.exit(0)
