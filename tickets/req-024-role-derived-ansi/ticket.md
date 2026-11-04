---
id: REQ-024
title: "Role-derived ANSI table (supersedes REQ-023)"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-024/
branch: ticket/req-024-role-derived-ansi
supersedes: REQ-023
---

# Role-derived ANSI table

## Requirement

Decision record (2026-11-04, JD-approved option **C**): the 16-color ANSI
projection must be **fully wallpaper/palette-derived**. Every slot maps directly
to a Material role from the selected mode; there are no fixed red/green/blue hue
anchors, no tint blend, no family bound, no hue-separation loop, and no derived
saturation. This supersedes REQ-023 option B (theme-tinted anchors), whose
implementation shipped in v0.5.2 and is replaced in v0.5.3.

No runtime or template change: `colors.kitty` and `colors.sequences` keep
consuming the one shared 16-`Color` tuple from `domain/ansi.py`.

### Facts to build on

- REQ-023 recipe being replaced:
  `src/theme_producer/domain/ansi.py` at commit `e0d9adf` (six hue anchors,
  `ANSI_HUE_TINT_MAX`, `ANSI_HUE_FAMILY_BOUND`, `ANSI_MIN_HUE_SEPARATION`,
  lightness and saturation windows).
- Canonical legacy order already used by the palette's `colors:` list:
  `src/theme_producer/domain/services.py:45-62` (`LEGACY_COLOR_ORDER`).
- Both projections consume `ansi_palette`:
  `src/theme_producer/adapters/projections/ansi.py:60-76`,
  `src/theme_producer/defaults/templates/colors.kitty.j2`,
  `colors.sequences.j2`.
- The templates use slot 0 for background/selection and slot 15 for
  foreground/cursor (`adapters/projections/ansi.py:31-39`).

### Design (normative)

`ANSI_SLOT_ROLES` is an explicit mapping of all sixteen slots in canonical
legacy order:

| Slot | Role | | Slot | Role |
| --- | --- | --- | --- | --- |
| 0 | `surface` | | 8 | `outline` |
| 1 | `error` | | 9 | `error_container` |
| 2 | `tertiary` | | 10 | `tertiary_container` |
| 3 | `secondary` | | 11 | `secondary_container` |
| 4 | `primary` | | 12 | `primary_container` |
| 5 | `surface_variant` | | 13 | `surface_container` |
| 6 | `outline_variant` | | 14 | `surface_container_high` |
| 7 | `on_surface` | | 15 | `on_surface_variant` |

Rules:

1. `ansi_palette(theme, mode)` returns `tuple(mode.roles[role] for role in
   ANSI_SLOT_ROLES in slot order)`; the selected mode is `theme.dark` by
   default and `theme.light` for `ModeName.LIGHT`. No color is generated.
2. Remove the hue-anchor, tint, family-bound, separation, normal/bright
   lightness, and saturation constants and helpers. `colorsys` is no longer
   imported by the module.
3. Keep the public output shape: a 16-element `tuple[Color, ...]`, so the
   templates and runtime need no changes.
4. Duplicate slot values are valid when the mode's roles coincide (common for a
   low-chroma wallpaper or fixed Material error tones). The recipe never
   fabricates a color to keep slots distinct.
5. The bright block 9..14 is the container-role block, not a lightness ramp:
   `error_container`, `tertiary_container`, `secondary_container`,
   `primary_container`, `surface_container`, `surface_container_high`.

### Accepted tradeoff

Standard ANSI semantics are intentionally not preserved: `color1` is no longer
red, `color2` is not green, `color4` is not blue. Each slot follows the
wallpaper's palette. JD accepts this; the terminal should match the wallpaper
rather than a fixed rainbow. A consequence is that foreground/cursor (slot 15)
now follow `on_surface_variant` instead of `on_surface`, while
background/selection still follow slot 0 (`surface`).

## Acceptance

- [x] `ANSI_SLOT_ROLES` explicitly maps all 16 slots to the roles above in
      canonical legacy order.
- [x] Hue-anchor, tint, family-bound, separation, and saturation logic removed;
      no fixed hue constants remain.
- [x] Dark and light tables select their own mode's roles.
- [x] Bright slots 9..14 equal their container roles.
- [x] Tests prove every slot equals its mapped role, mutating any mapped role
      changes that slot, and an unrelated role mutation does not.
- [x] Golden fixtures `tests/fixtures/projections/colors.kitty` and
      `colors.sequences` regenerated.
- [x] Before/after table for `default`, `white_tailed_eagle`, and
      `aurora_dragon` (all 16 slots, below) confirms every after value is a
      palette role.
- [x] Version `0.5.3` + `CHANGELOG.md` entry.
- [x] `make gates` green.

## Before/after (real wallpapers, dark mode)

Generated with the native engine on the host wallpapers; `before` is the
v0.5.2 REQ-023 table, `after` is this role mapping. A script asserted each
`after` value equals `theme.json.modes.dark.roles[role]`.

### default

| Slot | Role | Before | After |
| --- | --- | --- | --- |
| 0 | `surface` | `#121318` | `#121318` |
| 1 | `error` | `#d74242` | `#ffb4ab` |
| 2 | `tertiary` | `#42d7ba` | `#e5bad8` |
| 3 | `secondary` | `#4ed742` | `#c3c5dd` |
| 4 | `primary` | `#6042d7` | `#b9c3ff` |
| 5 | `surface_variant` | `#d742ca` | `#45464f` |
| 6 | `outline_variant` | `#4290d7` | `#45464f` |
| 7 | `on_surface` | `#c6c5d0` | `#e3e1e9` |
| 8 | `outline` | `#45464f` | `#90909a` |
| 9 | `error_container` | `#e68989` | `#93000a` |
| 10 | `tertiary_container` | `#89e6d4` | `#5c3c55` |
| 11 | `secondary_container` | `#91e689` | `#434659` |
| 12 | `primary_container` | `#9c89e6` | `#384379` |
| 13 | `surface_container` | `#e689de` | `#1f1f25` |
| 14 | `surface_container_high` | `#89bae6` | `#292a2f` |
| 15 | `on_surface_variant` | `#e3e1e9` | `#c6c5d0` |

### white_tailed_eagle

| Slot | Role | Before | After |
| --- | --- | --- | --- |
| 0 | `surface` | `#1a110e` | `#1a110e` |
| 1 | `error` | `#d77a42` | `#ffb4ab` |
| 2 | `tertiary` | `#42d742` | `#d5c68e` |
| 3 | `secondary` | `#bed742` | `#e7beaf` |
| 4 | `primary` | `#b242d7` | `#ffb59a` |
| 5 | `surface_variant` | `#d7426d` | `#53433e` |
| 6 | `outline_variant` | `#4267d7` | `#53433e` |
| 7 | `on_surface` | `#d8c2bb` | `#f1dfd9` |
| 8 | `outline` | `#53433e` | `#a08d86` |
| 9 | `error_container` | `#e6ac89` | `#93000a` |
| 10 | `tertiary_container` | `#89e689` | `#50471a` |
| 11 | `secondary_container` | `#d6e689` | `#5d4035` |
| 12 | `primary_container` | `#cf89e6` | `#72361e` |
| 13 | `surface_container` | `#e689a4` | `#271d1a` |
| 14 | `surface_container_high` | `#89a0e6` | `#322824` |
| 15 | `on_surface_variant` | `#f1dfd9` | `#d8c2bb` |

### aurora_dragon

| Slot | Role | Before | After |
| --- | --- | --- | --- |
| 0 | `surface` | `#171217` | `#171217` |
| 1 | `error` | `#d64242` | `#ffb4ab` |
| 2 | `tertiary` | `#42d6be` | `#f5b7b0` |
| 3 | `secondary` | `#cad642` | `#d6c0d6` |
| 4 | `primary` | `#8d42d6` | `#e9b5ef` |
| 5 | `surface_variant` | `#d642a7` | `#4d444c` |
| 6 | `outline_variant` | `#4267d6` | `#4d444c` |
| 7 | `on_surface` | `#cfc3cd` | `#eadfe7` |
| 8 | `outline` | `#4d444c` | `#988d97` |
| 9 | `error_container` | `#e68a8a` | `#93000a` |
| 10 | `tertiary_container` | `#8ae6d6` | `#673b36` |
| 11 | `secondary_container` | `#dee68a` | `#524153` |
| 12 | `primary_container` | `#b88ae6` | `#603768` |
| 13 | `surface_container` | `#e68ac8` | `#231e23` |
| 14 | `surface_container_high` | `#8aa1e6` | `#2e282d` |
| 15 | `on_surface_variant` | `#eadfe7` | `#cfc3cd` |

## Evidence / Verify

- Evidence: `src/theme_producer/domain/ansi.py` (full mapping),
  `tests/unit/domain/test_ansi.py`,
  `tests/unit/adapters/projections/test_ansi.py`,
  `tests/fixtures/projections/colors.kitty`,
  `tests/fixtures/projections/colors.sequences`.
- Test result: `uv run pytest -q -rs` → 645 passed, 88 skipped.
- Gates: `make gates` → exit 0 (test, lint, hermetic, lock-check, docs-check).
- Verify: `make gates` in `.worktrees/req-024/`; then
  `uv run pytest -q tests/unit/domain/test_ansi.py`.

## Follow-up

CAP-008 and AD-6 still describe hue-anchored ANSI. Their wording needs a
spec/architecture update through the normal OpenSpec/BMAD path; this ticket only
records and implements the terminal decision.

## Correction (2026-11-04): terminal chrome was a regression

The accepted tradeoff above notes that foreground/cursor follow slot 15
(`on_surface_variant`) after this change. Live output confirmed that consequence
was **not intended**: generated `colors.kitty`/`colors.sequences` rendered
`foreground #d7c1c1` and `cursor #d7c1c1` while the semantic `on_surface` was
`#f0dede`, visibly dimming terminal text.

This ticket's role table is unchanged and remains correct. The chrome mapping
was decoupled from slot indices by
[REQ-025](../req-025-terminal-chrome-semantic-roles/ticket.md) in v0.5.4:
`surface`/`on_surface` now drive background, foreground, cursor, and selection
regardless of which role occupies a slot. History above is kept as recorded; see
REQ-025 for the fix and regression tests.
