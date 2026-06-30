#!/usr/bin/env python3
"""Trim usage-lens.jsonl and remove stale /tmp files."""
import glob, json, os, sys, time

DEFAULTS = {"log_path": "~/.claude/usage-lens.jsonl", "cleanup_keep_days": 90}

def load_config():
    try:
        with open(os.path.expanduser("~/.config/usage-lens/config.json")) as f:
            return {**DEFAULTS, **json.load(f)}
    except Exception:
        return dict(DEFAULTS)

if __name__ == "__main__":
    cfg = load_config()
    log_path = os.path.expanduser(cfg["log_path"])
    keep_days = cfg["cleanup_keep_days"]
    cutoff_ms = (time.time() - keep_days * 86400) * 1000

    # Trim JSONL
    kept, removed = 0, 0
    if os.path.exists(log_path):
        lines = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    if json.loads(line).get("ts", 0) >= cutoff_ms:
                        lines.append(line)
                        kept += 1
                    else:
                        removed += 1
                except Exception:
                    lines.append(line)
                    kept += 1
        with open(log_path, "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"  log: kept {kept}, removed {removed} records")

    # Remove stale /tmp files
    stale = 0
    cutoff_s = time.time() - keep_days * 86400
    for p in glob.glob("/tmp/claude-usage-lens-*.txt"):
        try:
            if os.path.getmtime(p) < cutoff_s:
                os.remove(p)
                stale += 1
        except Exception:
            pass
    print(f"  /tmp: removed {stale} stale session files")
