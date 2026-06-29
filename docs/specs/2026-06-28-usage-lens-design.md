# usage-lens Design Spec
*2026-06-28*

## Overview

A skill that tracks and analyzes Claude Code skill invocations (and future: MCP tool calls) to surface usage patterns and recommendations. Initial release covers tracking and analysis; automatic enable/disable is a future improvement.

---

## Architecture

Three moving parts wired via Claude Code's hook system:

```
User prompt
    │
    ▼
[UserPromptSubmit hook]      →  writes prompt text to /tmp/claude-usage-lens-prompt.txt
    │
    ▼  (Claude invokes Skill tool)
[PostToolCall hook]          →  if tool == "Skill": read config + last prompt → append to JSONL
    │
    ▼
~/.claude/usage-lens.jsonl   (one line per invocation)
    │
    ▼  (user types /usage-lens)
[usage-lens skill]           →  calls analyze.py → stats + recommendations in conversation
```

### File layout

```
boring-skills/skills/usage-lens/
├── SKILL.md
└── scripts/
    ├── analyze.py           # analysis + report; also callable standalone
    ├── post_tool_hook.py    # PostToolCall handler
    └── prompt_hook.py       # UserPromptSubmit handler
```

External:
- `~/.config/usage-lens/config.json` — user config
- `~/.claude/usage-lens.jsonl` — event log (path overridable in config)

---

## Data Schema

### JSONL record

One JSON object per line. Fields present depend on verbosity level.

```json
{
  "ts": 1782691691492,
  "type": "skill",
  "name": "brainstorming",
  "session_id": "abc123",
  "project": "/Users/jinhuanlei/Documents/code/boring-skills",
  "trigger": "explicit"
}
```

| Field | Always present | Description |
|---|---|---|
| `ts` | yes | Unix timestamp (ms) |
| `type` | yes | Event type: `"skill"` today, `"mcp"` when extended |
| `name` | yes | Skill name or MCP tool name |
| `session_id` | standard + verbose | Claude Code session ID |
| `project` | standard + verbose | CWD of the session |
| `trigger` | standard + verbose | `"explicit"` (user typed `/name`) or `"auto"` (Claude decided) |
| `prompt` | verbose only | The user message that triggered the invocation |

**Trigger detection:** `prompt_hook.py` writes the raw user prompt to `/tmp/claude-usage-lens-prompt.txt` on every `UserPromptSubmit`. `post_tool_hook.py` reads it and checks if it starts with `/<name>` — yes → `"explicit"`, otherwise → `"auto"`.

### Config file (`~/.config/usage-lens/config.json`)

```json
{
  "verbosity": "standard",
  "log_path": "~/.claude/usage-lens.jsonl",
  "inactive_threshold_days": 30,
  "declining_window_days": 30
}
```

| Key | Default | Description |
|---|---|---|
| `verbosity` | `"standard"` | `"minimal"` \| `"standard"` \| `"verbose"` |
| `log_path` | `~/.claude/usage-lens.jsonl` | Where to write the event log |
| `inactive_threshold_days` | `30` | Days without use before "inactive" flag |
| `declining_window_days` | `30` | Window for trend comparison |

---

## Hooks

Two entries added to `~/.claude/settings.json` by the setup command:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/skills/usage-lens/scripts/prompt_hook.py"
          }
        ]
      }
    ],
    "PostToolCall": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/skills/usage-lens/scripts/post_tool_hook.py"
          }
        ]
      }
    ]
  }
}
```

No manual configuration required — `/usage-lens setup` patches `settings.json` automatically and creates the default config file.

---

## Analysis Script

`analyze.py` is the single analysis entry point. Callable standalone or invoked by the skill.

```bash
python analyze.py                    # full report (stdout)
python analyze.py --type skill       # filter by event type
python analyze.py --days 30          # limit to last N days
python analyze.py --json             # raw JSON for piping/scripting
```

### Report format

```
Usage Lens — last 30 days (127 events)

Skills
  brainstorming     ████████  24   last: 2h ago    ↑ trending
  auto-learnings    ██████    18   last: 1d ago
  tdd               ██        5    last: 8d ago
  gmail-spam-cleanup          0    last: 45d ago   ⚠ inactive

Recommendations
  • gmail-spam-cleanup — not used in 45 days, consider disabling
  • tdd — usage declining (was 12/mo, now 5/mo)
```

Recommendations are informational only in v1. Automatic enable/disable is a future improvement.

---

## Skill (`/usage-lens`)

Two modes:

- **`/usage-lens`** — run the full analysis report in-conversation
- **`/usage-lens setup`** — one-time setup: patch `settings.json`, create default config, confirm log path

The skill invokes `analyze.py` and presents output. If hooks are not yet configured (detected by checking `settings.json`), it prompts the user to run setup first.

---

## Extensibility

Adding MCP tool tracking later requires:
1. A new `PostToolCall` hook matcher for MCP tool names
2. The hook script emits `"type": "mcp"` with `"name": "gmail__send_email"` (or similar)
3. `analyze.py` already handles multiple types via `--type` filter — no changes needed

The JSONL schema and analysis script are type-agnostic by design.

---

## Out of Scope (v1)

- Automatic skill enable/disable
- Cross-user aggregation
- Web dashboard
- Backfilling from `history.jsonl`
