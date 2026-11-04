---
id: REQ-023
title: "Theme-tinted ANSI hue anchors with lower saturation"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-023/
branch: ticket/req-023-themed-ansi-anchors
---

# Theme-tinted ANSI hue anchors

## Requirement

Decision record (2026-11-04, JD-approved option **B**): the 16-color ANSI
projection must stop being a fixed rainbow. Keep the six standard ANSI hue
families, but tint each anchor part-way toward the theme's `primary` hue and
lower the saturation window. No runtime or projection template change: both
`colors.kitty` and `colors.sequences` keep consuming the one shared table from
`domain/ansi.py`.

### Facts to build on

- Current anchors and recipe: `src/theme_producer/domain/ansi.py:74-151`
  (red 25, green 145, yellow 90, blue 260, magenta 330, cyan 200; saturation
  `[0.45, 0.85]`, achromatic fallback `0.60`; normal/bright lightness
  `0.55/0.72` dark and `0.45/0.60` light).
- Slots 0/7/8/15 are Material roles; 9..14 are bright variants of 1..6.
- Both projections consume `ansi_palette`: `adapters/projections/ansi.py:60-76`,
  `src/theme_producer/defaults/templates/colors.kitty.j2`,
  `colors.sequences.j2`.

### Design (normative)

1. **Bounded hue tint.** For each anchor `a`, take the primary's HLS hue `p`
   (only when primary saturation is above the achromatic epsilon; otherwise do
   not tint). Move `a` toward `p` along the shortest circular arc by
   `f = ANSI_HUE_TINT_MAX`, then clamp the total movement from `a` to at most
   `ANSI_HUE_FAMILY_BOUND` degrees. Constants:
   - `ANSI_HUE_TINT_MAX = 0.30` (30% blend)
   - `ANSI_HUE_FAMILY_BOUND = 25.0` degrees
   - `ANSI_MIN_HUE_SEPARATION = 40.0` degrees
2. **Distinctness rule.** Compute all six tinted/clamped hues. If any pairwise
   shortest circular distance is below `ANSI_MIN_HUE_SEPARATION`, reduce the
   shared blend factor by `ANSI_HUE_TINT_STEP = 0.01` and recompute, repeating
   down to `0.0` (the current anchors). At `0.0` the original anchors are
   55-70 degrees apart, so the rule always terminates. The reduced factor is
   shared by all six slots so the palette stays coherent; it is deterministic.
3. **Lower saturation.** New window `[0.35, 0.65]`, achromatic fallback `0.50`,
   still derived from the primary with `colorsys.rgb_to_hls`. Lightness rules are
   unchanged: normal `0.55` dark / `0.45` light; bright `0.72` dark / `0.60`
   light.
4. **ANSI semantics.** Every slot stays within `25` degrees of its own anchor
   (family bound), so slot 1 remains red, slot 2 green, slot 3 yellow, slot 4
   blue, slot 5 magenta, slot 6 cyan; slot 9..14 reuse their normal slot's hue.
   Slots 0/7/8/15 keep their Material roles.
5. **No runtime change.** No CLI, engine, or template change. Only the shared
   domain table and its tests/goldens.

## Acceptance

- [ ] Same theme renders a deterministic 16-color table (repeat calls equal).
- [ ] Warm and cool primaries move all six chromatic hues toward the primary,
      while each stays within 25 degrees of its anchor.
- [ ] Minimum 40-degree circular separation holds for adversarial primaries
      (opposite hues, all six hue anchors, achromatic fallback).
- [ ] Saturation is inside `[0.35, 0.65]`, uses `0.50` for achromatic primary,
      and is lower than the old `[0.45, 0.85]` recipe on representative palettes.
- [ ] Dark and light tables both verified; bright variants share their normal
      slot's hue and are lighter; slots 0/7/8/15 still track Material roles.
- [ ] Golden fixtures `tests/fixtures/projections/colors.kitty` and
      `colors.sequences` regenerated for the new table.
- [ ] Before/after table printed for `default`, `white_tailed_eagle`, and
      `aurora_dragon` wallpapers (color1..6 + saturation), showing distinct,
      tinted hues.
- [ ] Version `0.5.2` + `CHANGELOG.md` entry.
- [ ] `make gates` green.

## Evidence / Verify

- Evidence: `src/theme_producer/domain/ansi.py` (current recipe),
  `tests/unit/domain/test_ansi.py`, `tests/unit/adapters/projections/test_ansi.py`.
- Verify: `make gates` in `.worktrees/req-023/`; then
  `uv run pytest tests/unit/domain/test_ansi.py -q`.
