# Design: Cross-Agent Auto-Learning Skill

**Date:** 2026-06-20
**Status:** Approved (design phase complete)
**Author:** Jinhuan Lei (with Claude)

## Problem

Coding agents forget. Corrections, stated preferences, durable project facts, and
hard-won debug insights from one session are gone by the next. Claude Code added a
native auto-memory (`MEMORY.md`) in v2.1.32+, but it is Claude-Code-specific.
Jinhuan uses several agents — opencode (running MiniMax-M3, glm-5.2), Claude Code,
and others — and wants one mechanism that persists learnings across all of them.

opencode (the primary target) has **no native auto-memory** — only static context
files (`AGENTS.md`, `CLAUDE.md`, and the `instructions` field in `opencode.json`).

## Goals

- Auto-capture four kinds of durable knowledge: **corrections, preferences, project
  facts, debug insights**.
- Persist them in an **agent-agnostic** store that any agent can read.
- Auto-recall them at the start of every session.
- Stay **generic for all agents** with a near-zero install footprint. Claude Code is
  a known, accepted exception (it reads `CLAUDE.md`, not `AGENTS.md`).

## Non-Goals

- No multi-agent install matrix or per-agent config patching.
- No Claude Code `CLAUDE.md` wiring in this version (out of scope; can be added later).
- No semantic search / embeddings / database. Plain markdown only.

## Architecture

A **pure SKILL.md + markdown store + exactly one shell script** design. The only thing
that ever touches the system is one managed instruction block in the global `AGENTS.md`,
written by the AI with the user's confirmation.

```
~/.learnings/
└── global.md                  # Global learnings (preferences + cross-project corrections/insights)

<project>/.learnings/
└── project.md                 # Project-specific learnings (incl. Project Facts)

<skill-dir>/
├── SKILL.md                   # All behavior: capture, dedup, recall, setup, management
└── log-learning.sh            # The ONLY script — mechanical capture (invoked by absolute path)
```

### Guiding principle

**Scripts are dumb and reliable; the AI is smart and flexible.** Anything requiring
judgment (deciding whether to capture, routing scope, dedup, editing the user's
`AGENTS.md`) is the AI's job. The single mechanical operation that benefits from
determinism — appending a correctly-formatted, correctly-timestamped entry to the
right section — is the script's job.

### Why exactly one script

Jinhuan runs weaker models (MiniMax-M3, glm-5.2) alongside Claude. The capture/append
operation is the highest-frequency mutation and the one most likely to be botched by a
smaller model: wrong section, malformed entry, hallucinated date. A tiny deterministic
script removes those risks. Every other operation (setup, recall, list, review, delete)
is infrequent and safe for the AI to do with its native tools, so none of them justify a
script.

### Why no `install.sh`

The script is invoked by its **absolute path inside the skill's own directory**
(`sh "$SKILL_DIR/log-learning.sh" ...`), so there is no PATH setup, no executable
installation, and no install script. Editing the user's `AGENTS.md` is a judgment edit
and is therefore handled by the AI's setup mode, never by a script (firm user rule:
**never blind-append to a user-owned config file**).

## Storage Format

One markdown file per scope. Identical structure for `global.md` and `project.md`. All
four section headers are always present (even when empty) so the script has stable
anchors to append against.

```markdown
# Learnings — <scope label>
<!-- learnings-skill schema: v1 | Entries: - [YYYY-MM-DD] (agent) text. Manual edits OK. -->

## Corrections
- [2026-06-20] (claude-code) Use `rg` not `grep -r` in this repo; grep is aliased to ripgrep.

## Preferences
- [2026-06-18] (opencode) Prefers POSIX sh over bash for portable scripts.

## Project Facts
- [2026-06-20] (opencode) Auth tokens live in Vault path `secret/app/api`, not env vars.

## Debug Insights
- [2026-06-19] (claude-code) Flaky test `test_sync` fails before `test_auth` — shared DB fixture.
```

**Format rules:**

- **Entry format:** `- [YYYY-MM-DD] (<agent>) <one-line content>`.
- **Source tag** `(<agent>)` records which agent captured the entry (provenance for
  multi-agent debugging).
- **Append order:** newest-last (chronological) — simplest, most reliable mechanical insert.
- **Single line per entry** — multi-line content is flattened to one line on capture.
- **Four sections always present**, even if empty.
- The **header comment** documents the contract (including a `schema: v1` version
  marker) so any agent reading the raw file understands the format and so migrate can
  detect and upgrade older files.

## Wiring & Recall (via global AGENTS.md)

Recall works by instructing the agent — not by importing file content. The AI's setup
mode adds a managed block to the global `AGENTS.md` (for opencode:
`~/.config/opencode/AGENTS.md`):

```markdown
<!-- BEGIN learnings-skill (managed) -->
## Persistent Learnings (auto-memory)
At the start of each session, read these files if they exist and treat their
contents as persistent memory you must respect:
- `~/.learnings/global.md` — global learnings (preferences, cross-project corrections & insights)
- `./.learnings/project.md` — learnings specific to the current project

When you learn something worth remembering — a correction, a stated preference,
a durable project fact, or a hard-won debug insight — capture it with the
learnings skill.
<!-- END learnings-skill -->
```

**Why this is generic:** `AGENTS.md` is the cross-agent standard (opencode, Cursor,
Copilot, Aider, etc. all read it). It is plain instruction text — no import mechanism
required, because agentic tools read the referenced files themselves with their own
file tools. This covers ~99% of non-Claude-Code agents with a single block.

**Known limitation (accepted):** an *instruction to read* depends on the agent actually
performing the read at session start. This is reliable for compliant agents but softer
than force-injecting content (e.g. opencode's `instructions` field). This trade is
accepted in exchange for generic reach.

## Behavior (defined in SKILL.md)

### Capture flow (core loop)

Every turn, the agent silently judges whether something durable just emerged. When a
signal fires, it acts **immediately in that same turn** (no batching — nothing is lost
if the session ends):

| Kind | Section | Example signal |
|------|---------|----------------|
| Correction | Corrections | "no, use X not Y", reverting the agent's code, "that's wrong" |
| Preference | Preferences | "I prefer…", "always/never…", stylistic asks |
| Project fact | Project Facts | durable truths about *this* repo (paths, conventions, gotchas) |
| Debug insight | Debug Insights | a non-obvious root cause / fix worth not rediscovering |

Steps when a signal fires:

1. **Route scope** — project-specific → `project.md`; cross-project or about-the-user
   → `global.md`.
2. **Dedup in-context** — compare against the already-loaded learnings. If a duplicate
   or conflict is found, surface it and ask: **skip / overwrite / append**.
3. **Confirm before writing** — show proposed `text`, scope, and section, and wait for
   the user's OK. **Every write is confirmed** (no silent writes).
4. **Capture** — call `log-learning.sh` with the chosen flags.

### Management (AI-driven, no scripts)

- **List** — "show my learnings" → AI reads the file(s) and prints them, grouped by section.
- **Review** — "review my learnings" → AI reads and flags stale / contradictory / duplicate
  entries and proposes edits.
- **Delete** — "forget X" → AI finds the matching entry, shows it, and removes it on confirm.

### Setup mode (AI-driven)

Triggered by "set up learnings" (or on first activation when `~/.learnings/` is missing):

1. Create `~/.learnings/` and seed `global.md` with the four-section skeleton.
2. Read the global `AGENTS.md`.
3. Propose where to insert the managed loading block (sensible placement, not a blind
   append).
4. Show the user the diff.
5. Write the block on confirm.

### Migrate mode (AI-driven, no script)

Triggered by "migrate learnings" / "import my notes into learnings" / "import CLAUDE.md".
Handles two jobs with one flow:

1. **Import** — ingest pre-existing knowledge (the user's `~/.claude/CLAUDE.md`, project
   notes, another agent's memory, a dumped skill) into the learnings store.
2. **Schema upgrade** — when the entry format or section set later changes, convert
   old-schema learnings to the current one. The `schema: vN` header marker tells migrate
   whether a file is out of date.

Flow (all AI judgment, then the existing script for writes):

1. **Identify source** — an explicit path the user provides, or auto-detect common ones
   (`~/.claude/CLAUDE.md`, an old-format `~/.learnings/*.md`, project notes).
2. **Read & extract** — pull individual knowledge items out of free-form text.
3. **Classify & route** — each item → one of the four sections, and global vs project scope.
4. **Normalize to current schema** — `- [YYYY-MM-DD] (agent) text`. Imported items, which
   usually lack a date and provenance, are stamped with the **migration date** and the
   agent tag `(migrated)` — e.g. `- [2026-06-20] (migrated) ...` — making clear they were
   imported rather than captured live.
5. **Dedup in-context** — skip items already present in the loaded learnings.
6. **Preview & confirm** — show the full set of proposed converted entries; the user approves.
7. **Write:**
   - *Imports* → call `log-learning.sh` per entry (same path as normal capture, keeps
     writes consistent).
   - *In-place schema upgrades* → the AI backs up the file first (`<file>.bak`), rewrites
     it to the current schema, then shows the diff.

## The `log-learning.sh` Contract

```
log-learning.sh --scope <global|project> \
                --section <corrections|preferences|facts|insights> \
                --agent <agent-name> \
                --text "<one-line content>"
```

Behavior (entirely mechanical, no judgment):

1. Resolve the target file: `global` → `~/.learnings/global.md`;
   `project` → `./.learnings/project.md`.
2. Map the short `--section` flag to its markdown header:
   `corrections` → `## Corrections`, `preferences` → `## Preferences`,
   `facts` → `## Project Facts`, `insights` → `## Debug Insights`.
   Reject any other value with a non-zero exit.
3. If the file or its directory is missing, create it with the four-section skeleton,
   including the `# Learnings` title and the `<!-- learnings-skill schema: v1 ... -->`
   header marker.
4. Flatten `--text` to a single line (collapse newlines and runs of whitespace).
5. Build the entry: `- [<date +%F>] (<agent>) <text>` — **the date comes from the
   system clock (`date +%F`), never from the model.**
6. Find the mapped `## <Header>` and insert the entry **newest-last** (immediately
   before the next `##` header, or at EOF if it is the last section).
7. Exit non-zero with a clear message on any failure (unknown section, unwritable
   path), so the AI notices and can fall back.

The AI is responsible for everything before the call (whether to capture, scope,
section, dedup, confirmation); the script is responsible only for writing the entry
correctly every time.

## Open Items / Future Work

- **Claude Code support** — add a `CLAUDE.md` loading line (out of scope for v1).
- **Force-injection for opencode** — optionally also use opencode's `instructions`
  field for harder guarantees than an AGENTS.md instruction (deferred; the generic
  approach is preferred for now).
- **git** — the project directory is not yet a git repo; initialize before
  implementation if version control is desired.
```
