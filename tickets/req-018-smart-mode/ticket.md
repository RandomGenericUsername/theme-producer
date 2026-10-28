---
id: REQ-018
title: "Smart projection mode: --mode smart"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-018/
branch: ticket/req-018-smart-mode
---

# Smart projection mode: --mode smart

## Requirement

Add `--mode smart` to `tpr generate` and `tpr show`.

- For an image source: compute the mean relative luminance of the image; choose `light` when the
  mean is ≥ 0.5, otherwise `dark`.
- For a color source: use the seed color's relative luminance with the same threshold.
- `theme.json` still carries both modes; the selected mode renders the eight consumer files.
- The engine is unchanged: `smart` is a `tpr` projection policy, not a color-generation mode.
- `--mode smart` is resolved before the container invocation; the inner command receives the
  concrete `dark`/`light`.
- `--dry-run` prints the resolved mode.
- Add Pillow as a runtime dependency for image luminance (both local and container images).
- Document the rule and that it is not matugen parity: matugen's own smart mode picked dark on the
  whole real corpus, so we use an explicit threshold instead of an opaque heuristic.

## Acceptance

- [ ] `--mode smart` on `generate`/`show`; default `dark` unchanged.
- [ ] Bright image → light; dark image → dark; threshold behavior tested.
- [ ] Color source uses its luminance.
- [ ] Container/dry-run receive the resolved concrete mode.
- [ ] Pillow in the package/image; tests cover the luminance helper.
- [ ] No new artifacts, no engine/catalog changes, no dotfiles changes.
- [ ] `make gates` green.

## Evidence

- `docs/CONTAINER-VALIDATION-v0.2.0-2026-10-28.md` (both modes available; dark default).
- matugen `--mode smart` probe: dark on all real wallpapers, including bright synthetic images.
