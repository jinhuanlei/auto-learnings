# Handoff: Cross-Agent Auto-Learning Skill

Portable handoff for picking this project up on a different agent or machine.

## What this project is

A custom agent **skill** that auto-captures "learnings" during coding sessions —
corrections, preferences, project facts, and debug insights — and persists them to an
**agent-agnostic** markdown store so future sessions (across opencode, Claude Code,
Cursor, Copilot, etc.) "remember." Inspired by Claude Code's native auto-memory
(`MEMORY.md`), but designed to work across agents, with opencode as the primary target.

## Current status

**Design phase complete.** Full spec written and approved through all design sections.
Not yet started: implementation plan, or any skill code.

- **Spec (source of truth):** `docs/superpowers/specs/2026-06-20-learnings-skill-design.md`
- **Next step:** create the implementation plan (use the `writing-plans` skill), then
  build the skill (use `skill-creator`).
- The project dir is **not yet a git repo**.

## Locked design decisions

Architecture: **pure SKILL.md + markdown store + exactly one shell script.**

| Area | Decision |
|------|----------|
| Capture scope | Corrections + Preferences + Project Facts + Debug Insights |
| Store | `~/.learnings/global.md` + `<project>/.learnings/project.md` |
| Format | 4 fixed sections; entries `- [YYYY-MM-DD] (agent) text`; **newest-last**; **source tag included**; header carries `schema: v1` marker |
| Capture trigger | AI judges every turn; acts **immediately** (no batching) |
| Confirm policy | **Confirm every write** before logging |
| Dedup | AI dedups in-context (learnings are auto-loaded); on dup/conflict ask skip/overwrite/append |
| Scope routing | AI decides project vs global |
| Recall / wiring | AI-driven **setup mode** adds a managed block to the global `AGENTS.md` instructing the agent to read the learnings files at session start. **No blind appends to user configs** — judgment edits are the AI's job, shown as a diff + confirmed. Generic for ~99% of non-Claude-Code agents. |
| Scripts | **Only one:** `log-learning.sh`, invoked by absolute path inside the skill dir (no install.sh, no PATH/exec footprint). Exists because weak models (MiniMax-M3, glm-5.2) would botch markdown appends/timestamps. |
| Setup / list / review / delete / migrate | **All AI-driven**, no scripts |
| Migrate mode | AI-driven import (CLAUDE.md, notes, other agents' memory, dumped skills) + schema upgrade. Imported entries stamped `(migrated)` with the migration date. Imports call `log-learning.sh`; in-place schema upgrades back up the file first, then rewrite + diff. |

### `log-learning.sh` contract

```
log-learning.sh --scope <global|project> \
                --section <corrections|preferences|facts|insights> \
                --agent <agent-name> \
                --text "<one-line content>"
```
Mechanical only: resolve file → map section flag to header (`facts`→`## Project Facts`,
`insights`→`## Debug Insights`) → create skeleton (with `schema: v1`) if missing →
flatten text to one line → build `- [<date +%F>] (<agent>) <text>` (date from system,
never the model) → insert newest-last in the section → non-zero exit on any failure.

### Guiding principle

**Scripts are dumb and reliable; the AI is smart and flexible.** Only the
highest-frequency, determinism-sensitive operation (capture) is scripted. Everything
requiring judgment is the AI's job.

## Environment notes

- Primary working dir: `/Users/jinhuanlei/Documents/code/self-learning-skill`
- Skills live in `~/.claude/skills/` (shared by opencode via Claude Code compat)
- opencode global config: `~/.config/opencode/` has **two** files — `opencode.json`
  (plugins/mcp) and `opencode.jsonc` (permissions/providers). Neither has an
  `instructions` field. (We chose the AGENTS.md approach, so this no longer matters
  for wiring, but note it if revisiting.)
- opencode has **no native auto-memory** — only static `AGENTS.md` / `CLAUDE.md` /
  `instructions` field.
- opencode global AGENTS.md target: `~/.config/opencode/AGENTS.md`.
- Claude Code is the **accepted exception** (reads `CLAUDE.md`, not `AGENTS.md`) — its
  wiring is out of scope for v1.

## Suggested skills (in order)

1. **`writing-plans`** — create the implementation plan from the spec (the terminal
   transition from brainstorming).
2. **`skill-creator`** — scaffold and build the skill once the plan exists.

## Open items / future work

- Claude Code `CLAUDE.md` wiring (deferred).
- Optional opencode `instructions`-field force-injection for harder recall guarantees
  (deferred; AGENTS.md instruction preferred for genericity).
- `git init` the project before implementation if version control is wanted.
