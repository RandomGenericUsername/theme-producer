---
id: BUG-003
title: "GTK/rasi legacy tokens missing: AGS and rofi break on a tpr palette"
kind: bug
status: done
lane: 1
severity: high
links:
  openspec: none
  bmad: none
worktree: .worktrees/bug-003/
branch: ticket/bug-003-legacy-token-compat
repro: "uv run tpr generate <image> -o /tmp/tpr && rg 'color_foreground' /tmp/tpr/colors.gtk.css; rg '@define-color color04' /tmp/tpr/colors.rasi"
observed: "GTK css has no color_background/color_foreground/color_cursor; rasi has @define-color color4 (no zero padding), so AGS @color_foreground/@color_background and rofi @color04/@color01/@color07/@color10 are undefined."
expected: "GTK css emits color_background, color_foreground, color_cursor and color_00..15; rasi emits zero-padded color00..15; a compatibility test pins both sets."
---

# GTK/rasi legacy tokens missing

## Repro

```bash
cd /home/inumaki/Development/dotfiles/theme-producer
uv run tpr generate <image> -o /tmp/tpr
rg 'color_foreground|color_background|color_cursor' /tmp/tpr/colors.gtk.css
rg '@define-color color04|@define-color color00' /tmp/tpr/colors.rasi
```

## Observed

- `colors.gtk.css` has `background`, `foreground`, and `color_00..15`, but not
  `color_background`, `color_foreground`, `color_cursor`.
- `colors.rasi` has `color0..15` (not zero-padded), so `@color04`, `@color01`, `@color07`,
  `@color10` are undefined.

## Expected

- GTK: `color_background`, `color_foreground`, `color_cursor`, `color_00..15` (CSG parity).
- Rasi: `color00..15` (CSG parity); rofi uses `@color04`/`@color01`/`@color07`/`@color10`.
- Compatibility test asserts the exact legacy token sets.

## Impact

AGS uses `@color_foreground`/`@color_background` across the bar/notifications/capture/icme/
btop-studio/wallpaper-selector; rofi uses zero-padded rasi names. Without this, switching the
runtime to a tpr palette loses text/background colors and rofi theming.

## Fix notes

Update `colors.gtk.css.j2` and `colors.rasi.j2`; update projection goldens; add
`tests/unit/adapters/projections/test_compatibility_tokens.py`. Bump to `0.3.1`; rebuild images.
