---
id: REQ-026
title: "Project the selected palette mode into colors.yaml"
kind: requirement
status: done
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

- [x] The selected mode is emitted in every generated `colors.yaml` as a
      top-level quoted `mode` scalar.
- [x] Dark is the default (`mode: "dark"`); `--mode light` emits
      `mode: "light"` from `theme.json.modes.light`.
- [x] Projection goldens/fixtures and template/content tests assert the mode
      key; all eight runtime artifacts still render under one invocation.
- [x] Consumer compatibility is exercised read-only: ITR preserves the scalar,
      the dotfiles runtime detects the mode, and any rejecting reader is named
      with the chosen representation recorded.
- [x] `make gates` green; hermetic suite green; `make ci-gates-parity` green.
- [x] Release the next appropriate version on a tagged commit, merged
      fast-forward to `master`, pushed with the tag.

## Evidence / Verify

- Evidence: `dotfiles-runtime/src/runtime/adapters/appearance.py:76-77`
  (`_MODE_KEYS`, `_DARK_BOOL_KEYS`) and `:134-171`
  (`detect_palette_mode`); pre-change `defaults/templates/colors.yaml.j2`
  emits only roles + the legacy list.
- Verify: render `tests/fixtures/theme.json` in both modes and inspect the
  first line of `colors.yaml`; then run the runtime detector on that file.

## Progress / evidence (build)

Implementation commit: `486942a` on `ticket/req-026-palette-mode-projection`
(worktree `.worktrees/req-026/`).

### What landed

- `src/theme_producer/defaults/templates/colors.yaml.j2` emits
  `mode: "{{ mode_name }}"` immediately after the header. `mode_name` is the
  existing selected-mode string on `ProjectionContext`
  (`adapters/projections/registry.py:283`), so no processor/CLI contract
  changed: the same eight filenames, the same `--mode` flag, and both modes in
  `theme.json`.
- Exact emitted value: line 2 is `mode: "dark"` for the default/dark selection
  and `mode: "light"` for `--mode light` (a `smart` run emits its resolved
  concrete mode). Roles, produced `on_backdrop`, and the legacy `colors:` list
  are unchanged.
- `tests/fixtures/projections/colors.yaml` now carries `mode: "dark"`;
  `test_mode.py` asserts `mode: "light"` and the literal second line for the
  light render; `test_template_content.py` accepts/asserts the mode scalar;
  `tests/integration/test_cli_local.py` asserts the light CLI artifact carries
  `mode: "light"` while all eight runtime files are present.
- `README.md`, `CHANGELOG.md`, `pyproject.toml`, `src/theme_producer/__init__.py`
  and `uv.lock` are at `0.6.0`.

### Consumer compatibility (read-only siblings)

Command: `FileColorSchemeLoader().load(generated colors.yaml)` from
`icon-templates-renderer/.venv` (ITR accepts additive top-level scalars):

```text
mode= dark
background= #000000
colors= 16
```

Command: `runtime.adapters.appearance.detect_palette_mode(generated colors.yaml)`
from `dotfiles-runtime`:

```text
mode= dark
values_mode= dark
```

Command: `parsePaletteYaml(generated colors.yaml)` from `ags-platform` (Node
26, TypeScript strip-types):

```text
REJECT dark PaletteParseError colors-dark.yaml:2: role "mode" has invalid value "dark" (expected #rgb, #rrggbb or #rrggbbaa)
REJECT light PaletteParseError colors-light.yaml:2: role "mode" has invalid value "light" (expected #rgb, #rrggbb or #rrggbbaa)
```

**Chosen representation and reason:** a top-level quoted `mode` scalar is the
safest representation. It is the runtime's first-precedence key, ITR preserves
it, and it is ordinary generated YAML. No scalar can satisfy both the runtime
and the current AGS reader: every runtime mode key (`mode`/`scheme`/
`appearance`/`variant`/`is_dark`/`dark`) has a `dark`/`light`/boolean value,
which AGS rejects because it treats every non-`version`/`colors` top-level
scalar as a hex role. The AGS reader needs a companion change to skip palette
metadata (as it already does for `version`); its `createTheme.apply()` failure
policy keeps the legacy CSS path installed until then. Siblings were not
edited.

### Commands and results

- `uv run pytest -q -rs` → **649 passed, 88 skipped**.
- `make gates` → **exit 0** (`test` 649 passed/88 skipped, `lint` clean,
  `hermetic` 645 passed/37 skipped, `lock-check` resolved 34 packages,
  `docs-check` pass).
- `make ci-gates-parity` → **PASS** gates
  `[docs-check, hermetic, lint, lock-check, test]`; jobs include `image` as
  declared CI-only.
- `make build` → **exit 0** (`dist/theme_producer-0.6.0.tar.gz`,
  `dist/theme_producer-0.6.0-py3-none-any.whl`).
- Verify: `make gates && make ci-gates-parity` in `.worktrees/req-026/`.

## Outcome

Released `v0.6.0` (tag on this branch), merged fast-forward to `master`, and
pushed with the tag.
