---
id: REQ-013
title: "v2 Rust helper on material-colors + oracle parity"
kind: requirement
status: proposed
lane: 3 — ticket-multi
parent: EPIC-001
links:
  openspec: req-013-native-engine
  bmad: none
worktree: none
branch: none
---

# v2 Rust helper on material-colors + oracle parity

## Requirement

Replace matugen as the default engine with our own Rust helper on the MIT/Apache-2.0
`material-colors` crate, behind the same `ThemeEnginePort`.

## Acceptance

- [ ] Rust helper (~200–400 LOC) emits the `theme.json` shape; crate and toolchain pinned; MIT/
      Apache notices carried.
- [ ] `Dockerfile.native` builds the helper; `--engine native` selects it; matugen remains available
      for parity.
- [ ] Oracle parity tests run both engines on a wallpaper corpus and assert roles/tones within a
      recorded tolerance.
- [ ] No GPL dependency; `make gates`, `make image` green.
- [ ] The pure-Python engine remains an explicit non-goal (no v3 ticket).

## Done-when

`pytest tests/contract -q -k engine_parity` green and `tpr generate --engine native` produces a
schema-valid Theme.

