---
id: REQ-025
title: "Decouple terminal chrome from ANSI slot indices"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-025/
branch: ticket/req-025-terminal-chrome-semantic-roles
fixes_regression_from: REQ-024
---

# Decouple terminal chrome from ANSI slot indices

## Requirement

`REQ-024` changed ANSI slot 15 from `on_surface` to `on_surface_variant`, but left
the kitty/OSC chrome mapping pointing at slot indices. As a result `colors.kitty`
and `colors.sequences` render `foreground`, `cursor`, and `selection_foreground`
from `on_surface_variant` instead of the semantic `on_surface`. That dims
terminal text and was not intended by the role-derived palette decision.

This ticket is a correction to `REQ-024`, not a rewrite of it. The role-derived
16-slot table stays exactly as specified there; only the terminal chrome keys are
decoupled from it.

### Normative design

1. `build_ansi_context()` keeps `colors` as the unchanged 16-slot
   `ansi_palette()` table, but resolves chrome directly from the selected mode's
   Material roles:
   - `background` = `surface`
   - `foreground` = `on_surface`
   - `cursor` = `on_surface`
   - `selection_background` = `surface`
   - `selection_foreground` = `on_surface`
2. Remove the `ANSI_BACKGROUND_INDEX`, `ANSI_FOREGROUND_INDEX`,
   `ANSI_CURSOR_INDEX`, `ANSI_SELECTION_BACKGROUND_INDEX`, and
   `ANSI_SELECTION_FOREGROUND_INDEX` constants. Add a comment stating that
   chrome is semantic and must never be derived from a slot index again.
3. Add dark/light tests asserting every chrome key equals its role, plus a
   regression test where slot 15 differs from `on_surface` and asserting kitty
   `foreground`/`cursor` and OSC 10/12 use `on_surface`.
4. Regenerate the ANSI goldens and verify the default fixture foreground is
   `on_surface` (`#fbd0aa`), not slot 15 (`#000000`).
5. Ship as version `0.5.4`.

### Known live evidence

Before the fix, a generated theme printed `foreground #d7c1c1` and
`cursor #d7c1c1` (slot 15, `on_surface_variant`) while the semantic
`on_surface` was `#f0dede`. After the fix the same theme must render
`#f0dede` for both.

## Acceptance

- [x] `build_ansi_context()` resolves chrome from selected-mode Material roles,
      never from ANSI slot indices.
- [x] The misleading slot-index constants are removed and cannot regress
      silently.
- [x] Dark and light tests assert background/cursor/selection semantics.
- [x] Regression test proves an `on_surface_variant` != `on_surface` theme
      renders `on_surface` for kitty foreground/cursor and OSC 10/12.
- [x] ANSI role-table tests remain green.
- [x] Golden fixtures regenerated; default foreground/cursor are `on_surface`.
- [x] Version `0.5.4` + `CHANGELOG.md` entry.
- [x] `make gates` green; `make ci-gates-parity` green.
- [x] `REQ-024` carries a correction note linking here.

## Evidence / Verify

- Evidence: `src/theme_producer/adapters/projections/ansi.py`,
  `tests/unit/adapters/projections/test_ansi.py`,
  `tests/unit/adapters/projections/test_mode.py`,
  `tests/fixtures/projections/colors.kitty`,
  `tests/fixtures/projections/colors.sequences`,
  `CHANGELOG.md`.
- Verify: `make gates && make ci-gates-parity` in `.worktrees/req-025/`.
