---
id: ops-002
title: "Sync BUG-004 INDEX status and acceptance with the shipped v0.5.1 tag"
kind: ops-task
status: done
lane: direct
links:
  openspec: none
  bmad: none
worktree: .worktrees/ops-002/
branch: ticket/ops-002-index-status-sync
---

# Sync BUG-004 INDEX status and acceptance with the shipped v0.5.1 tag

## Work

`bug-004-rasi-projection` is `done` with a complete Outcome (fixed in `v0.5.1`,
deployed via PIN-0129, live rofi parse verified), but `tickets/INDEX.md` still
said `in-progress` and the acceptance boxes were unchecked.

- Tick the five acceptance items; the Outcome supplies the evidence.
- Set the INDEX line to `done` with `tag: v0.5.1`.

## Done-when

BUG-004 frontmatter, acceptance, Outcome, and INDEX all agree that the fix
shipped in `v0.5.1`.

## Evidence

- `tickets/bug-004-rasi-projection/ticket.md` — Outcome.
- `tickets/INDEX.md` — `done`, `tag: v0.5.1`.
- `git tag --sort=-creatordate` → `v0.5.1`.
