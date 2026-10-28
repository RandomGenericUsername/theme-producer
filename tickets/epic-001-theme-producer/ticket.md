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

5/16 done.

  - [x] `OPS-001` — Repo birth + planning substrate (`done`)
  - [x] `REQ-001` — Product brief (`done`)
  - [x] `REQ-002` — Spec (CAP-001..012) (`done`)
  - [x] `REQ-003` — Architecture spine (AD-1..13) (`done`)
  - [x] `REQ-004` — Executable harness: packaging, gates, CI, hermetic tests (`done`)
  - [ ] `REQ-005` — Theme domain model + alias vocabulary (`proposed`)
  - [ ] `REQ-006` — Settings via config-assembler-engine (`proposed`)
  - [ ] `REQ-007` — ThemeEnginePort + matugen engine + engines.yaml (`proposed`)
  - [ ] `REQ-008` — Canonical theme.json + open projections (`proposed`)
  - [ ] `REQ-009` — ANSI intent projection (kitty, sequences) (`proposed`)
  - [ ] `REQ-010` — CLI surface + local/container/dry-run processors (`proposed`)
  - [ ] `REQ-011` — Pinned base + matugen images, install/uninstall (`proposed`)
  - [ ] `REQ-012` — contracts record + conformance test (blocked) (`proposed`)
  - [ ] `REQ-013` — v2 Rust helper on material-colors + oracle parity (`proposed`)
  - [ ] `REQ-014` — Dotfiles runtime/provisioning adoption (after spike) (`proposed`)
  - [ ] `SPIKE-001` — Dotfiles fit: adapter, hashes, contract, rollout (`boxed`)

## Exec links

- brief: `_bmad-output/theme-producer/brief-theme-producer/brief-theme-producer.md`
- spec: `_bmad-output/theme-producer/spec-theme-producer/spec-theme-producer.md`
- spine: `_bmad-output/theme-producer/architecture-theme-producer/architecture-theme-producer.md`
