# Consumer capability audit — 2026-10-28

Read-only audit of every dotfiles consumer of the palette artifacts. No dotfiles edits were made.
The producer-side compatibility fixes are in `BUG-003` and stay in `theme-producer`.

## Method

- Read the runtime consumer pointers (`dotfiles-runtime/src/runtime/adapters/consumer_path_spec.py:48-57`).
- Read every consumer template/config under `dotfiles-assets`, `ags-apps`, `ags-platform`,
  `dotfiles-provision/ansible`, and `dotfiles-runtime/src`.
- Counted token references per file (`@color_*`, `colorN`, `COLOR_*`).
- Compared the live CSG artifacts with the `tpr` projections.

## Artifact → consumer map

| Artifact | Delivered via | Consumers |
|---|---|---|
| `colors.gtk.css` | `config/ags/colors.css` pointer | AGS bar/apps, GTK3, wlogout (via `COLORS_FILE_PATH`) |
| `colors.adw.css` | `config/gtk-4.0/colors.css` pointer | GTK4 / libadwaita apps |
| `colors.yaml` | ITR `ICON_RENDERER__COLOR_SCHEME__PATH`; AGS apps read the current pointer | icons, icme, btop-theme-studio |
| `colors.rasi` | `config/rofi/colors.rasi` pointer | rofi |
| `colors.conf` | `current/colors.conf` direct read | hyprland |
| `colors.btop.theme` | `config/btop/themes/colors.btop.theme` pointer | btop |
| `colors.kitty` | `current/colors.kitty` include | kitty |
| `colors.sequences` | `current/colors.sequences` cat | zsh / terminal |
| `theme.json` | producer-side only | no consumer today |

## Consumer matrix

| Consumer | Current tokens (evidence) | Format capability | Migration |
|---|---|---|---|
| AGS bar | `@color_foreground` ×103, `@color_background` ×3, `@color_00..15` (`ags-apps/bar/style.css:3,75`) | open: GTK CSS `@define-color` | map foreground/background to `on_surface`/`surface`; role-map accents |
| AGS notifications | `@color_foreground` ×26, `@color_06` ×20, `@color_03` ×16 (`ags-apps/notifications/style.css`) | open | `@color_06`→`primary`/`surface_tint`; `@color_03`→`outline_variant` (per app) |
| AGS capture-tool | `@color_foreground` ×45, `@color_background` ×10, `@color_06` ×10 (`ags-apps/capture-tool/style.css:31,54,82`) | open | same role mapping |
| AGS icme | `@color_foreground` ×46, `@color_10` ×14, `@color_03` ×13 (`ags-apps/icme/style.css`) | open | same |
| AGS btop-theme-studio | `@color_foreground` ×19, `@color_06` ×6 (`ags-apps/btop-theme-studio/style.css`) | open | same |
| AGS wallpaper-selector | `@color_foreground` ×22, `@color_background` ×6 (`ags-apps/wallpaper-selector/style.css`) | open | same |
| AGS hypr-pano (legacy) | `@color_foreground` ×9, `@color_06` ×8, `@color_00..15` (`ags-apps/hypr-pano/style.css`) | open | same; legacy only |
| wlogout | `@color_15`, `@color_12`, `@color_07` (`dotfiles-assets/templates/wlogout/style.css.tpl:20,34,37`) | open | `@color_15`→`on_surface`, `@color_12`→`primary`, `@color_07`→`on_surface_variant` |
| rofi | `@background`, `@foreground`, `@color01`, `@color04`, `@color07`, `@color10` (`dotfiles-assets/configs/rofi/launcher/config.rasi:18-95`) | open: rasi `@define-color` | map `@color04`→`primary`, `@color01`→`surface_container`, `@color07`→`on_surface_variant`, `@color10`→`primary_fixed_dim` |
| hyprland | `$color0`, `$color1`, `$color2`, `$color6`, `$color10`, `$color12` (`dotfiles-assets/configs/hypr/colors.lua:42-51`) | open: `$var` | optional; map to accent roles |
| btop | semantic keys (`main_bg`, `main_fg`, `title`, `hi_fg`, `cpu_*`, …) | fixed semantic | none |
| kitty | ANSI `color0..15` | fixed ANSI | keep |
| zsh / terminal | ANSI sequences | fixed ANSI | keep |
| icons / ITR | `COLOR_FOREGROUND` ×23, `COLOR_ACCENT: color13` ×13, `COLOR_BACKGROUND: color15` ×12, `color0` ×8, `color6` ×3, `color12` ×3, `background` ×2, `color3` ×1, `color1` ×1; defaults `surface`/`accent`/`accent-muted` (`dotfiles-assets/icons/mappings/defaults.yaml:16-18`) | open: arbitrary keys | phase 1: migrate variant overrides to roles; keep `colorN` fallback |
| btop-theme-studio | `colors.yaml` `background:`, `foreground:`, `- "hex"` list; `colors.btop.theme` (`ags-apps/btop-theme-studio/ui/StudioWindow.tsx:84-99,105`) | open subset | no change |
| icme | `colors.yaml` (current pointer; token reader) (`ags-apps/icme/lib/inputs.ts:56`) | open | no change if role keys are present |
| GTK3 / GTK4 apps | `colors.gtk.css` / `colors.adw.css` pointers | open: named colors + CSS custom properties | app styles can use roles incrementally; no in-repo app styles to change |
| AGS platform | applies `~/.config/ags/colors.css` | n/a | none |

## Compatibility gaps in `tpr` (fixed in v0.3.1)

These were producer bugs, not consumer design choices. `BUG-003` fixed them in `v0.3.1`; the
compatibility test now pins both alias sets.

1. **GTK CSS lacks `color_background`, `color_foreground`, `color_cursor`.**
   - Live CSG emits them (`color-scheme-generator/.../colors.gtk.css.j2:1-3`; live
     `current/colors.gtk.css:1-3`).
   - AGS styles consume `@color_foreground` and `@color_background` heavily
     (`ags-apps/bar/style.css:3,75`; notifications/capture/icme/etc.).
   - `tpr`’s `colors.gtk.css.j2` emits `background`/`foreground` and `color_00..15`, but not the
     three aliases.
2. **Rasi positional aliases are not zero-padded.**
   - Live CSG emits `color00..color15` (`color-scheme-generator/.../colors.rasi.j2`).
   - Rofi uses `@color01`, `@color04`, `@color07`, `@color10`
     (`dotfiles-assets/configs/rofi/launcher/config.rasi:18,19,57,94`).
   - `tpr`’s `colors.rasi.j2` emits `color0..color15` (no zero padding), so those names are
     undefined.

Non-blocking differences (no consumer found):

- `colors.yaml` omits `source_image`, `backend`, `generated_at`. ITR preserves extras; icme and
  btop-theme-studio use only `background`/`foreground`/the `colors` list, which `tpr` emits.
- `colors.conf` omits `$cursor`. Hyprland reads only `$color0..15`; no consumer uses `$cursor`.
- `colors.adw.css` emits `color_00..15` but not `color_background`; CSG’s ADW artifact also did not
  emit those aliases, and no GTK4 consumer uses them.

## Migration plan (after the compatibility fix)

| Phase | Scope | Risk | Proof |
|---|---|---|---|
| 0 | Add `color_background`/`color_foreground`/`color_cursor` to GTK; zero-pad rasi aliases; compatibility test | none; additive | golden assertion of the exact legacy token set |
| 1 | Icons: migrate variant `colorN` overrides to roles where semantics are clear; keep `colorN` fallback | medium: contrast/icon guard | icon render + contrast tests |
| 2 | wlogout + rofi: map positional tokens to roles | low–medium: visual | screenshot + rasi/gtk parse |
| 3 | AGS apps (bar, notifications, capture, icme, btop-studio, wallpaper-selector): per-app role mapping | medium: state colors/hover/focus | app screenshots + per-app visual check |
| 4 | GTK/adw app styles; hypr optional | low | visual |
| — | kitty/sequences stay ANSI; btop already semantic | none | — |

Rules for migration:

- Keep `@color_foreground` / `@color_background` / `color_N` as compatibility aliases for one
  release; migrate consumers incrementally.
- Map by **role**, not by index: `@color_06` is not “primary” everywhere; each app uses it for a
  different state. Preserve state colors (success/warning/error) explicitly.
- Do not rename artifacts; the runtime contract freezes the eight filenames.
- Light mode is producer-ready but the runtime still consumes dark; consumer light/dark switching is
  a separate runtime feature.

## Verdict

The dependency map is now explicit. The producer is compatible for **icons, btop, kitty, zsh,
hypr, wlogout** once the two alias bugs are fixed; **rofi** needs the zero-padded rasi aliases; AGS
apps need the GTK aliases and can then migrate to roles incrementally. No consumer is inherently
blocked from semantics except kitty/sequences, which are ANSI by design.
