---
id: REQ-015
title: "Native source-color parity: prefer + fallback_color"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-015/
branch: ticket/req-015-native-source-parity
---

# Native source-color parity: prefer + fallback_color

## Requirement

Make the native engine choose source colors the way matugen does for image inputs, and expose
matugen's selection controls.

- `prefer` (`darkness`, `lightness`, `saturation`, `less-saturation`, `value`,
  `closest-to-fallback`) selects among the ranked candidate colors.
- `fallback_color` is used when extraction yields no acceptable color and for
  `closest-to-fallback`.
- `source_color_index` continues to select a ranked candidate.
- Default selection (no `prefer`) matches matugen on the real-wallpaper corpus.
- The matugen adapter forwards `--prefer`; the native helper implements it.

## Clean-room rule

matugen is GPL-2.0-or-later. Use it ONLY as a behavioral oracle (run it, observe outputs, read its
CLI help/docs). Do NOT read, copy, or line-by-line translate its source. Implement from observed
behavior and the MIT/Apache `material-colors` crate.

## Acceptance

- [ ] `engines.yaml` exposes `prefer` (choices above) and `fallback_color` for both engines.
- [ ] matugen adapter forwards `--prefer` and `--fallback-color`.
- [ ] native helper implements all six preferences and fallback; invalid hex/unknown preference
  fails clearly.
- [ ] Oracle corpus: seven real wallpapers × six preferences; native source_color/primary matches
  matugen exactly or within ±1, with the remaining deltas recorded.
- [ ] Unit tests cover the ranking/preference selection and fallback without the binary.
- [ ] `make gates` green; no dotfiles/contracts/provisioning changes.

## Evidence

- `docs/CONTAINER-VALIDATION-2026-10-28.md` — zenitsu source divergence.
- matugen `--help` / `--prefer` semantics and the `material-colors` `score`/`quantize` APIs.
- `theme-producer` native adapter, catalog, and `native/src/main.rs`.
