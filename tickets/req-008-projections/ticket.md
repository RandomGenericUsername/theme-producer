---
id: REQ-008
title: "Canonical theme.json + open projections"
kind: requirement
status: proposed
lane: 3 — ticket-multi
parent: EPIC-001
links:
  openspec: req-008-projections
  bmad: none
worktree: none
branch: none
---

# Canonical theme.json + open projections

## Requirement

Write the canonical `theme.json` schema and the open/semantic projections. Each projection is a pure
function of `Theme`; capability tables are contract data.

## Acceptance

- [ ] `schemas/theme.schema.json` (versioned) and a writer that validates before writing.
- [ ] Projections: `colors.gtk.css`, `colors.adw.css`, `colors.yaml`, `colors.rasi`,
      `colors.btop.theme`, `colors.conf`, plus dev-only `theme.html`.
- [ ] `colors.gtk.css`/`colors.adw.css` emit the stable vocabulary + full roles + legacy
      `color_00..15`; `colors.yaml` emits aliases + all roles + legacy list; `colors.rasi` and
      `colors.conf` emit semantic variables + legacy aliases; btop uses an explicit 48-key mapping
      table.
- [ ] Every projection declares `open` or `fixed` and has a golden test; a mutation test proves a
      role change only affects dependent projections.
- [ ] No projection emits an unknown key for its format (kitty excluded; REQ-009).
- [ ] `make gates` green.

## Done-when

`pytest tests/unit/adapters/projections -q` green; `theme.json` validates against the schema.

