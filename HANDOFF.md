# Handoff: auto-learnings Skill

Portable handoff for picking this project up on a different agent or machine.

## What this project is

A custom agent **skill** that auto-captures "learnings" during coding sessions —
corrections, preferences, project facts, and debug insights — and persists them to an
**agent-agnostic** markdown store so future sessions (across opencode, Claude Code,
Rovo Dev, Cursor, etc.) "remember."

## Current status

**Implementation complete.** Skill is built, tested, committed, and pushed.

- **Repo:** `github.com/jinhuanlei/auto-learnings`
- **Local dir:** `/Users/leijinhuan/Documents/code/auto-learnings`
- **Skills install:** `~/.claude/skills/auto-learnings` → symlink to local dir (live)
- **Spec:** `docs/superpowers/specs/2026-06-20-learnings-skill-design.md`

### Committed files

| File | Purpose |
|------|---------|
| `SKILL.md` | All skill behavior |
| `log-learning.sh` | The only script — mechanical append |
| `evals/evals.json` | 3 test cases |
| `README.md` | User-facing usage guide |
| `.gitignore` | Ignores workspace/, *.bak, .DS_Store, HANDOFF.md |

### Gitignored

- `auto-learnings-workspace/` — eval run artifacts from skill-creator
- `HANDOFF.md` — this file

## Locked design decisions (unchanged from original)

Architecture: **pure SKILL.md + markdown store + exactly one shell script.**

| Area | Decision |
|------|----------|
| Capture scope | Corrections + Preferences + Project Facts + Debug Insights |
| Store | `~/.learnings/global.md` + `<project>/.learnings/project.md` |
| Format | 4 fixed sections; entries `- [YYYY-MM-DD] (agent) text`; newest-last; source tag included; header carries `schema: v1` marker |
| Capture trigger | AI judges every turn; acts immediately (no batching) |
| Confirm policy | Confirm every write before logging |
| Dedup | AI dedups in-context; on dup/conflict ask skip/overwrite/append |
| Scope routing | Heuristic list: path/convention → project; style/cross-project → global; uncertain → ask |
| Scripts | Only one: `log-learning.sh`, invoked by absolute path `~/.claude/skills/auto-learnings/log-learning.sh` |
| Setup / list / review / delete / migrate | All AI-driven, no scripts |

## Setup mode — supported agents

| Agent | Config file |
|-------|------------|
| opencode | `~/.config/opencode/AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` |
| Rovo Dev | `~/.rovodev/AGENTS.md` |
| Cursor / Other | user provides path |

## Agent name tags

| Agent | `--agent` tag |
|-------|--------------|
| Claude Code | `claude-code` |
| opencode | `opencode` |
| Rovo Dev | `rovo-dev` |

## Grilling decisions (all locked)

| # | Decision |
|---|----------|
| 1 | Script path hardcoded: `~/.claude/skills/auto-learnings/log-learning.sh` |
| 2 | Confirmation UI: structured block Scope/Section/Text + yes/no/edit |
| 3 | Dedup: semantic same-meaning, lean toward flagging, show both side-by-side |
| 4 | append-on-conflict: immediately after existing entry (AI writes directly, not script) |
| 5 | Agent name map: claude-code, opencode, rovo-dev; fallback short lowercase |
| 6 | Setup trigger: auto-prompt on first capture if ~/.learnings/ missing; explicit anytime |
| 7 | Missing AGENTS.md/CLAUDE.md: create it, show full new file in diff, single confirm |
| 8 | Block placement: AI reads file and picks most natural spot by judgment |
| 9 | edit behavior: ask "What would you like to change?" → regenerate → loop |
| 10 | Script failure: report error, stop. No fallback write. |
| 11 | Scope routing: heuristic list; uncertain → ask |
| 12 | Delete: AI file tools only; script stays append-only |
| 13 | Migrate ambiguity: Unclassified bucket in preview; user assigns before write |
| 14 | Activation: always-on capture; management commands on explicit request only |
| 15 | Recall wiring: AGENTS.md/CLAUDE.md block only; SKILL.md assumes learnings loaded |

## Migration plan (from self-improvement skill)

- **Decision:** Option A — migrate then retire
- **self-improvement skill location:** `~/.rovodev/skills/self-improvement/`
- **Trigger:** `migrate learnings` — user will provide path to their LEARNINGS.md at runtime
- **Format difference:** self-improvement uses rich LRN-xxx structured entries; auto-learnings uses one-liners. Migrate extracts the `Learning:` field from each entry.

## Open items

- **Description optimizer:** `run_loop.py` was running when session closed. Iteration 1 showed recall=0% (skill not auto-triggering). Kill with `kill $(pgrep -f run_loop)` if still running. Re-run with:
  ```sh
  cd ~/.claude/skills/skill-creator
  python3 -m scripts.run_loop \
    --eval-set /Users/leijinhuan/Documents/code/auto-learnings/auto-learnings-workspace/trigger-eval-set.json \
    --skill-path /Users/leijinhuan/Documents/code/auto-learnings \
    --model claude-sonnet-4-6 \
    --max-iterations 5 \
    --verbose
  ```
  If it finished, results are in `/tmp/run_loop.log` — look for `best_description` and apply to SKILL.md frontmatter.

- **Cursor AGENTS.md path:** unknown, user to provide at setup time.
- **self-improvement retirement:** pending migration being run.
