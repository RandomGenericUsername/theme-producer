---
id: REQ-005
title: "Theme domain model + alias vocabulary"
kind: requirement
status: in-progress
lane: 2 — openspec-single
parent: EPIC-001
links:
  openspec: req-005-domain-theme-model
  bmad: none
worktree: .worktrees/req-005/
branch: ticket/req-005-domain-theme-model
---

# Theme domain model + alias vocabulary

## Requirement

Implement the pure domain: `Color`, `Source`, `GeneratorMetadata`, `TonalPalette`, `Mode`, `Role`,
`Theme`, plus the alias vocabulary service. No I/O.

## Acceptance

- [ ] Frozen dataclasses with validation: hex `^#[0-9a-fA-F]{6}$`; exactly 50 roles per mode; six
      palettes (`primary secondary tertiary neutral neutral_variant error`); 18 tones each
      (0,5,10,15,20,25,30,35,40,50,60,70,80,90,95,98,99,100); both `dark` and `light`.
- [ ] Alias vocabulary resolves the stable eight (`background foreground accent accent-muted
      surface on_surface error warning`) plus the legacy `color0..15` indices.
- [ ] A golden `theme.json` fixture round-trips into `Theme` and back without loss.
- [ ] Tests cover invalid hex, missing role, wrong palette count, wrong tone set.
- [ ] `make gates` green.

## Done-when

`pytest tests/unit/domain -q` green, including the golden fixture round-trip.

