---
id: EPIC-001
title: "Theme producer (successor to CSG)"
kind: epic
status: in-progress
lane: 4 — bmad-advisory
links:
  openspec: none
  bmad: brief-theme-producer, spec-theme-producer, architecture-theme-producer
worktree: none
branch: main
children:
  - OPS-001
  - REQ-001
  - REQ-002
  - REQ-003
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-008
  - REQ-009
  - REQ-010
  - REQ-011
  - REQ-012
  - REQ-013
  - REQ-014
  - SPIKE-001
done-when: "A pinned tpr release produces a schema-valid Theme and the eight projections; the adoption spike reports a mechanical CSG swap; gates and image smoke are green."
---

# Theme producer (successor to CSG)

## Done-when

A pinned `tpr` release produces a schema-valid `theme.json` plus the eight projection files; every
projection is a pure function of the Theme; the ANSI projection is intentional (not a luminance
ramp); `make gates`, `make build` and `make image` are green; `spike-001-dotfiles-fit` reports a
mechanical CSG swap with the runtime's artifact/hash impact named.

## Children

20/21 complete (19 done + 1 spike reported; REQ-014 blocked).

  - [x] `OPS-001` — Repo birth + planning substrate (`done`)
  - [x] `REQ-001` — Product brief (`done`)
  - [x] `REQ-002` — Spec (CAP-001..012) (`done`)
  - [x] `REQ-003` — Architecture spine (AD-1..13) (`done`)
  - [x] `REQ-004` — Executable harness: packaging, gates, CI, hermetic tests (`done`)
  - [x] `REQ-005` — Theme domain model + alias vocabulary (`done`)
  - [x] `REQ-006` — Settings via config-assembler-engine (`done`)
  - [x] `REQ-007` — ThemeEnginePort + matugen engine + engines.yaml (`done`)
  - [x] `REQ-008` — Canonical theme.json + open projections (`done`)
  - [x] `REQ-009` — ANSI intent projection (kitty, sequences) (`done`)
  - [x] `REQ-010` — CLI surface + local/container/dry-run processors (`done`)
  - [x] `REQ-011` — Pinned base + matugen images, install/uninstall (`done`)
  - [x] `REQ-012` — contracts record + conformance test (`done`)
  - [x] `REQ-013` — v2 Rust helper on material-colors + oracle parity (`done`)
  - [x] `BUG-001` — Native engine advertises scheme-smart but rejects it (`done`)
- [x] `BUG-002` — Default container image_tag is latest, not the pin (`done`)
- [ ] `REQ-014` — Dotfiles runtime/provisioning adoption (after spike) (`proposed`)
- [x] `REQ-015` — Native source-color parity: prefer + fallback_color (`done`)
- [x] `REQ-016` — Native lightness controls: lightness_dark / lightness_light (`done`)
- [x] `REQ-017` — Light-mode projections: --mode dark|light (`done`)
  - [x] `SPIKE-001` — Dotfiles fit: adapter, hashes, contract, rollout (`reported`)

## Exec links

- brief: `_bmad-output/theme-producer/brief-theme-producer/brief-theme-producer.md`
- spec: `_bmad-output/theme-producer/spec-theme-producer/spec-theme-producer.md`
- spine: `_bmad-output/theme-producer/architecture-theme-producer/architecture-theme-producer.md`
