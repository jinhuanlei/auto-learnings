#!/usr/bin/env python3
"""PostToolUse hook — logs Skill invocations to usage-lens.jsonl."""
import sys, os, json, time, fcntl

DEFAULTS = {
    "verbosity": "standard",
    "log_path": "~/.claude/usage-lens.jsonl",
}

def load_config():
    try:
        with open(os.path.expanduser("~/.config/usage-lens/config.json")) as f:
            return {**DEFAULTS, **json.load(f)}
    except Exception:
        return dict(DEFAULTS)

try:
    data = json.load(sys.stdin)
    skill_name = data.get("tool_input", {}).get("skill", "unknown")
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd", "")

    trigger = "unknown"
    try:
        with open(f"/tmp/claude-usage-lens-{session_id}.txt") as f:
            prompt = f.read()
        trigger = "explicit" if prompt.strip().startswith(f"/{skill_name}") else "auto"
    except Exception:
        pass

    cfg = load_config()
    verbosity = cfg.get("verbosity", "standard")
    log_path = os.path.expanduser(cfg.get("log_path", DEFAULTS["log_path"]))

    record = {"ts": int(time.time() * 1000), "type": "skill", "name": skill_name}
    if verbosity in ("standard", "verbose"):
        record.update({"session_id": session_id, "project": cwd, "trigger": trigger})

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(record) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)

except Exception as e:
    try:
        with open(os.path.expanduser("~/.claude/usage-lens-errors.log"), "a") as f:
            f.write(f"post_tool_hook: {e}\n")
    except Exception:
        pass

sys.exit(0)
