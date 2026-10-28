---
id: REQ-015
title: "Native source-color parity: prefer + fallback_color"
kind: requirement
status: done
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

## Known divergences (2026-10-28)

Oracle corpus: 8 images × 7 selections = 56 pairs. **41/56 exact or ±1**, 15 recorded
divergences. Default (no `prefer`) is exact on 6/7 real wallpapers; zenitsu/yasuke still pick a
different candidate. Root cause: matugen 4.2.0 vendors a `material-colors` fork, so its candidate
list differs before preference selection. We did not read its source (clean-room); the test pins
every divergent pair so a change is visible.

The native extraction grid moved to 112×112 Triangle to match matugen's observed candidate list;
this improved default parity from 1/7 to 6/7 and changes image-sourced native themes slightly.

## Evidence

- `docs/CONTAINER-VALIDATION-2026-10-28.md` — zenitsu source divergence.
- matugen `--help` / `--prefer` semantics and the `material-colors` `score`/`quantize` APIs.
- `theme-producer` native adapter, catalog, and `native/src/main.rs`.
