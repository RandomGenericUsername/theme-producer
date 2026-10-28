---
id: REQ-018
title: "Smart projection mode: --mode smart (configurable threshold)"
kind: requirement
status: done
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-018/
branch: ticket/req-018-smart-mode
---

# Smart projection mode: --mode smart (configurable threshold)

## Requirement

Add `--mode smart` to `tpr generate` and `tpr show`, with the decision rule configurable.

- Image source: mean relative luminance of the image; `light` when the mean is **≥ threshold**,
  otherwise `dark`.
- Color source: use the seed color's relative luminance with the same threshold.
- `theme.json` still carries both modes; the selected mode renders the eight consumer files.
- The engine is unchanged: `smart` is a `tpr` projection policy, not a color-generation mode.
- `--mode smart` is resolved before the container invocation; the inner command receives the
  concrete `dark`/`light`.
- `--dry-run` prints the resolved mode.

Configuration:

- `[output] default_mode = "dark" | "light" | "smart"` (default `dark`).
- `[output] smart_threshold = 0.5` (float, 0..1).
- CLI `--mode dark|light|smart` overrides `default_mode`.
- CLI `--smart-threshold <0..1>` overrides `smart_threshold`.
- Env overrides: `THEME__OUTPUT__DEFAULT_MODE`, `THEME__OUTPUT__SMART_THRESHOLD`.
- `dump-config` serializes both fields; `info` reports them.
- Add Pillow as a runtime dependency for image luminance.
- Document the rule and that it is not matugen parity: matugen's own smart mode picked dark on the
  whole real corpus, including bright synthetic images.

## Acceptance

- [ ] `--mode smart` on `generate`/`show`; default comes from `output.default_mode` (packaged default
  `dark`).
- [ ] `output.smart_threshold` is configurable via settings, env and `--smart-threshold`.
- [ ] Bright image → light; dark image → dark; changing the threshold changes the decision (e.g.
  mean ~0.6: `0.5` → light, `0.8` → dark).
- [ ] Color source uses its luminance.
- [ ] Container/dry-run receive the resolved concrete mode.
- [ ] Pillow in the package/image; tests cover the luminance helper.
- [ ] No new artifacts, no engine/catalog changes, no dotfiles changes.
- [ ] `make gates` green.

## Evidence

- `docs/CONTAINER-VALIDATION-v0.2.0-2026-10-28.md` (both modes available; dark default).
- matugen `--mode smart` probe: dark on all real wallpapers, including bright synthetic images.
