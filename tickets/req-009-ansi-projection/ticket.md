---
id: REQ-009
title: "ANSI intent projection (kitty, sequences)"
kind: requirement
status: done
lane: 3 — ticket-multi
parent: EPIC-001
links:
  openspec: req-009-ansi-projection
  bmad: none
worktree: .worktrees/req-009/
branch: ticket/req-009-ansi-projection
---

# ANSI intent projection (kitty, sequences)

## Requirement

Generate a deliberate 16-color ANSI palette from the Theme (hue-anchored, theme-derived tone/chroma)
and render `colors.kitty` and `colors.sequences` from the same table.

## Acceptance

- [ ] Recipe documented: color0/7 from surface/on_surface, color8 outline, 1–6 hue anchors, 9–15
      bright variants; chroma/tone derived from the seed/contrast.
- [ ] Hue-window assertions for the six slots; contrast assertions for 0/7; no duplicate collapse on
      a low-chroma fixture.
- [ ] Both projections consume one shared table; kitty emits only valid keys; sequences uses the
      documented binary post-processing.
- [ ] `make gates` green.

## Done-when

`pytest tests/unit/adapters/ansi -q` green; kitty and sequences are byte-identical to the shared
table render.

