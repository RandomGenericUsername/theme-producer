---
id: REQ-026
title: "Project the selected palette mode into colors.yaml"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-026/
branch: ticket/req-026-palette-mode-projection
---

# Project the selected palette mode into `colors.yaml`

## Requirement

`tpr generate` already selects one Theme mode (`dark` default, `light`, or a
concrete mode resolved from `smart`) for the eight consumer projections, and
`theme.json` carries both modes. But the generated `colors.yaml` carries no mode
metadata, so the dotfiles runtime cannot tell which mode the palette bytes
represent.

The runtime resolves the appearance mode from the palette itself:
`dotfiles-runtime/src/runtime/adapters/appearance.py:134-171` accepts a
top-level `mode`/`scheme`/`appearance`/`variant` scalar (`dark`/`light`) or
`is_dark`/`dark` boolean, and falls back to `dark` when none is present. That
fallback makes every generated palette look dark, so `mode.light` skin overrides
are unreachable.

### Normative design

1. The projection context already exposes the selected mode as `mode_name`
   (`src/theme_producer/adapters/projections/registry.py`,
   `ProjectionContext.mode_name`). Emit it as a quoted top-level
   `mode: "dark"` / `mode: "light"` scalar in `colors.yaml`.
2. Keep the rest of the artifact byte-stable: roles, produced `on_backdrop`, and
   the legacy `colors:` list are unchanged; only the mode line is additive.
3. Do not change the invocation contract: same eight filenames, same CLI flags,
   `theme.json` still carries both modes.
4. Document the emitted key in `README.md` and `CHANGELOG.md`.
5. Record consumer compatibility for `itr`'s `FileColorSchemeLoader`, the
   dotfiles runtime mode detector, and the AGS `parsePaletteYaml` reader.

## Acceptance

- [ ] The selected mode is emitted in every generated `colors.yaml` as a
      top-level quoted `mode` scalar.
- [ ] Dark is the default (`mode: "dark"`); `--mode light` emits
      `mode: "light"` from `theme.json.modes.light`.
- [ ] Projection goldens/fixtures and template/content tests assert the mode
      key; all eight runtime artifacts still render under one invocation.
- [ ] Consumer compatibility is exercised read-only: ITR preserves the scalar,
      the dotfiles runtime detects the mode, and any rejecting reader is named
      with the chosen representation recorded.
- [ ] `make gates` green; hermetic suite green; `make ci-gates-parity` green.
- [ ] Release the next appropriate version on a tagged commit, merged
      fast-forward to `master`, pushed with the tag.

## Evidence / Verify

- Evidence: `dotfiles-runtime/src/runtime/adapters/appearance.py:76-77`
  (`_MODE_KEYS`, `_DARK_BOOL_KEYS`) and `:134-171`
  (`detect_palette_mode`); pre-change `defaults/templates/colors.yaml.j2`
  emits only roles + the legacy list.
- Baseline: `uv run pytest -q -rs` on the ticket worktree.
- Verify: render `tests/fixtures/theme.json` in both modes and inspect the
  first line of `colors.yaml`; then run the runtime detector on that file.
