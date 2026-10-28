# Container validation — 2026-10-28

Scope: prove the containerized theme producer works on real wallpapers **without matugen installed on the
host**, for both engine images, and that its output is the nine-artifact theme the runtime expects.

## Method

- Host: `command -v matugen` → absent; `~/.cache/matugen` and `~/.config/matugen` → absent.
- Images (podman, `v0.1.0`):
  - `tpr-matugen-podman:v0.1.0` (353 MB)
  - `tpr-native-podman:v0.1.0` (344 MB)
- Command shape (host CLI, container engine, no host engine binary):
  ```bash
  uv run tpr --output-format json generate <wallpaper> \
    --engine <matugen|native> --runtime container --container-engine podman \
    -o /tmp/opencode/tpr-validation/<name>-<engine>
  ```
- Wallpapers: six real files from `~/.local/share/dotfiles/wallpapers/` plus the currently applied
  wallpaper from the runtime cache
  (`~/.local/state/dotfiles/cache/wallpapers/fb1c5be…/wallpaper.png`).

## Result

Every run: exit 0, `success: true`, **9 files**, 50 roles, 6 palettes × 18 tones, 16 distinct ANSI
colors, hue anchors exactly on 25° / 145° / 90° / 260° / 330° / 200°.

| Wallpaper | matugen | native | matugen primary | native primary |
|---|---:|---:|---|---|
| zenitsu-agatsuma 4K | 13.6 s | 13.6 s | `#e3c36c` | `#ffb4a3` |
| windows-95-dark 4K | 14.3 s | 13.5 s | `#82d3e2` | `#81d3e0` |
| gargantua-black 4K | 13.6 s | 13.4 s | `#9fcafc` | `#9ecafc` |
| japan-artistic 4K | 13.8 s | 13.5 s | `#ffb4a9` | `#ffb4a9` |
| astronaut-purple 4K | 14.3 s | 13.7 s | `#f6b2e0` | `#f7b1de` |
| yasuke-dark 8K | 15.4 s | 14.4 s | `#ffb3ad` | `#ffb3ac` |
| current wallpaper | 13.2 s | 13.1 s | `#b9c3ff` | `#bac3ff` |

- 8K wallpaper handled in ~15 s including container startup.
- `theme.json` validated against `schemas/theme.schema.json` for both engines.
- `colors.yaml` carries `surface`, `on_surface`, `accent`, `accent-muted`, `primary`, and the legacy
  `colors:` list; `colors.gtk.css` carries the semantic names plus `color_00..15`; `colors.btop.theme`
  carries the semantic keys (`main_bg`, `main_fg`, `title`, `hi_fg`, `cpu_*`); kitty has 16 distinct
  ANSI colors.
- No host matugen cache/config was created: the container runs with `HOME=/tmp`.

## Finding: native is not a visual drop-in for every image

With the **same seed color** the two engines are exact (50 roles + 108 tones, 0 deltas). With an
**image source** they can choose a different source color:

```
zenitsu  matugen source_color #f9c711  primary #e3c36c
         native  source_color #f13802  primary #ffb4a3
```

Other wallpapers differ only by ±1 per channel (rounding), e.g. windows-95 151/316 values, yasuke
40/316. The zenitsu case is a real divergence in source-color selection, not rounding.

Consequence: **for the first live cutover, keep `engine = "matugen"`** (the packaged default) so the
look matches what was evaluated. Use `native` only after aligning its source-color selection with
matugen's preference, or accept the difference explicitly.

## Consumer follow-up

The artifacts are present and semantically richer, but the consumer-side adoption is still separate:

- icons: mappings still often use `colorN`; `surface`/`accent`/`accent-muted` are now real.
- wlogout: `@color_15` / `@color_12` can move to semantic names.
- rofi: `@colorN` can move to semantic names.
- AGS/GTK: styles can move from `@color_N` to role names incrementally.
- btop is already semantic; kitty/sequences stay 16 ANSI by design.

## Reproduce

```bash
cd /home/inumaki/Development/dotfiles/theme-producer
uv run tpr --output-format json generate \
  "$HOME/.local/share/dotfiles/wallpapers/zenitsu-agatsuma-3840x2160-26517.png" \
  --engine matugen --runtime container --container-engine podman \
  -o /tmp/opencode/tpr-validation/repro
ls /tmp/opencode/tpr-validation/repro   # theme.json + eight projections
```
