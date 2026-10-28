---
id: REQ-016
title: "Native lightness controls: lightness_dark / lightness_light"
kind: requirement
status: done
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-016/
branch: ticket/req-016-native-lightness-controls
---

# Native lightness controls: lightness_dark / lightness_light

## Requirement

Expose and implement matugen's per-mode lightness controls on the native engine:

- `lightness_dark` (float, default 0): for the dark scheme, an affine transform that keeps
  lightness 1 at 1 and moves lightness 0 to the argument, then clamps.
- `lightness_light` (float, default 0): for the light scheme, an affine transform that keeps
  lightness 0 at 0 and moves lightness 1 to `1 + argument`, then clamps.
- The matugen adapter forwards `--lightness-dark` / `--lightness-light`; the native helper
  implements them and applies them per mode after scheme generation.
- Both flags are exposed in `engines.yaml` for both engines.

## Clean-room rule

matugen is GPL-2.0-or-later. Use it only as a black-box oracle (run it, observe outputs, read its
`--help`). Do NOT read or copy its source. Implement from observed behavior and the MIT/Apache
`material-colors` crate.

## Acceptance

- [ ] `engines.yaml` exposes `lightness_dark` and `lightness_light` (float, default 0) for matugen
  and native.
- [ ] matugen adapter forwards both flags; native helper parses both, applies the per-mode affine
  transform, clamps, and emits both modes.
- [ ] Invalid numeric values fail clearly; extremes are clamped.
- [ ] Oracle: seed colors / contrast / lightness values (`-1, -0.5, 0, 0.5, 1`) on the real corpus;
  native roles match matugen exactly or within the recorded tolerance; deltas recorded.
- [ ] Unit tests for the affine transform and CLI forwarding.
- [ ] `make gates` green; no dotfiles/contracts/provisioning changes.

## Evidence

- matugen `--help` description of `--lightness-dark` / `--lightness-light`.
- `docs/CONTAINER-VALIDATION-2026-10-28.md` and the REQ-015 oracle harness.
- `native/src/main.rs`, `src/theme_producer/adapters/engines/{native,matugen}.py`.
