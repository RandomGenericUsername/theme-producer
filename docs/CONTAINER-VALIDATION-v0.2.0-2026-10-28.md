# Container validation — v0.2.0 (2026-10-28)

Scope: the `v0.2.0` container images, both engines, dark and light projections, `prefer`, and
`lightness`, on real wallpapers. **No dotfiles/provisioning/runtime changes.**

## Isolation

The host currently has a provisioned `theme-producer/settings.toml` (from the earlier
provisioning slice) that pins `v0.1.0`; a bare `tpr` picks it up through XDG. Standalone runs used:

```bash
uv run tpr --output-format json \
  --config /tmp/opencode/tpr-standalone-settings.toml \
  --templates-dir src/theme_producer/defaults/templates \
  generate <wallpaper> --engine <matugen|native> \
  --runtime container --container-engine podman \
  --mode <dark|light> -o <out> [--param ...]
```

The temp config pins `image_tag = "v0.2.0"`, `runtime.mode = "container"`, `engine = "matugen"`.
Host matugen is absent; both `tpr-matugen-podman:v0.2.0` and `tpr-native-podman:v0.2.0` were used.

## Base matrix — 7 wallpapers × 2 engines × dark/light

All 28 runs: exit 0, **9 files**, 50 roles, 6 palettes × 18 tones, **16 distinct ANSI colors**,
schema-valid `theme.json`, 13–16 s including container startup (8K ~16 s).

| Wallpaper | Matugen dark → light surface | Native dark → light surface | Light artifacts match |
|---|---|---|---|
| zenitsu 4K | `#16130b` → `#fff8f1` | `#1a110f` → `#fff8f6` | both |
| windows-95 4K | `#0e1416` → `#f5fafc` | `#0e1416` → `#f5fafc` | both |
| gargantua 4K | `#101418` → `#f8f9ff` | `#111318` → `#f9f9ff` | both |
| japan 4K | `#1a1110` → `#fff8f7` | `#1a1110` → `#fff8f7` | both |
| astronaut 4K | `#181215` → `#fff7f9` | `#181215` → `#fff7f9` | both |
| yasuke 8K | `#1a1110` → `#fff8f7` | `#1a1110` → `#fff8f7` | both |
| current | `#121318` → `#fbf8ff` | `#121318` → `#fbf8ff` | both |

`--mode light` writes the light roles to the same eight filenames; `theme.json` always carries both
modes. Verified: `colors.yaml` `surface`/`on_surface` and `colors.kitty` `background` equal the
light-mode roles for every case.

ANSI hue anchors in light mode are still 25° / 145° / 90° / 260° / 330° / 200° (within 0.5°), and
all 16 slots are distinct.

## Default dark: matugen vs native

Exact (source + primary) on windows-95, japan, astronaut, yasuke, current. Divergent:

- **zenitsu**: matugen `#f9c711` / `#e3c36c`; native `#f94e06` / `#ffb59e`.
- **gargantua**: matugen `#0f1318` / `#9fcafc`; native `#1b1d21` / `#a6c8ff` (small).

This is the known candidate-list difference from matugen's vendored `material-colors` fork.

## `prefer` (subset: zenitsu, windows-95)

| Preference | zenitsu | windows-95 |
|---|---|---|
| darkness | different | exact |
| lightness | **exact** | different |
| saturation | **exact** | **exact** |
| less-saturation | different | exact |
| value | different | exact |
| closest-to-fallback | requires `fallback_color` | requires `fallback_color` |

`closest-to-fallback` correctly fails without a fallback; with `--param fallback_color=#123456` it
succeeds for both engines on both wallpapers (9 files).

## `lightness_*`

Tested on zenitsu with `lightness_dark=0.5`, `lightness_dark=-0.5`, `lightness_light=0.5`:
all runs succeed, 9 files. At `-0.5` the surface clamps to `#000000` and the ANSI set collapses to
15 distinct colors (clamping, not a failure). The oracle suite (`REQ-016`) covers the numeric parity:
2489/2500 roles exact, 2500/2500 within ±1.

## Conclusion

- The `v0.2.0` containerized producer is validated standalone on real wallpapers: dark/light,
  `prefer`, `lightness`, both engines, no host matugen.
- Light mode is real: same eight consumer filenames, light roles, both modes in `theme.json`.
- Matugen remains the visual reference for zenitsu/gargantua; native is exact on the other five.
- No dotfiles, provisioning, runtime, contracts, or v3 changes were made for this validation.

## Reproduce

```bash
cd /home/inumaki/Development/dotfiles/theme-producer
uv run tpr --output-format json \
  --config /tmp/opencode/tpr-standalone-settings.toml \
  --templates-dir src/theme_producer/defaults/templates \
  generate "$HOME/.local/share/dotfiles/wallpapers/zenitsu-agatsuma-3840x2160-26517.png" \
  --engine matugen --runtime container --container-engine podman \
  --mode light -o /tmp/opencode/tpr-v020-smoke
```
