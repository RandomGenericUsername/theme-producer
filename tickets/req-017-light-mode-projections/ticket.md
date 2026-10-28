---
id: REQ-017
title: "Light-mode projections: --mode dark|light"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-017/
branch: ticket/req-017-light-mode-projections
---

# Light-mode projections: --mode dark|light

## Requirement

The Theme already carries both modes; the projections currently render only dark. Add a projection
mode selector so light mode can be generated and tested without changing the artifact contract.

- `tpr generate IMAGE --mode dark|light` (default `dark`) renders the selected mode into the same
  eight filenames.
- `tpr show IMAGE --mode dark|light` displays the selected mode.
- `theme.json` always contains both modes.
- `LocalProcessor`, `ContainerProcessor` and `DryRunProcessor` carry the mode; the container inner
  command forwards `--mode`.
- No new artifact names, no runtime/provisioning change.

Out of scope: `smart` mode (engine/`tpr` policy), runtime light/dark switching, new light artifact
filenames, consumer-side theme switching. Those are a follow-up.

## Acceptance

- [ ] `--mode dark|light` on `generate` and `show`; default `dark` keeps existing output
  byte-identical for the same theme.
- [ ] Light output's `colors.*` roles match `theme.json.modes.light` (goldens); dark output matches
  `theme.json.modes.dark`.
- [ ] `theme.json` always has both modes.
- [ ] `--dry-run` prints the selected mode; container mode forwards it; no new files.
- [ ] `theme.html` shows both modes (or lets the viewer switch) while the eight consumer files use
  the selected mode.
- [ ] Unit + integration tests; `make gates` green; no dotfiles/contracts/provisioning changes.

## Evidence

- `theme.json` has both modes (`docs/CONTAINER-VALIDATION-2026-10-28.md`).
- Current projections render dark (`adapters/projections/registry.py`).
