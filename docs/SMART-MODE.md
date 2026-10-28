# Smart projection mode

`tpr generate` and `tpr show` accept `--mode dark|light|smart`. This is a **projection policy**,
not a color-generation mode: the engine still produces one Theme with both `dark` and `light`
modes, and `theme.json` always carries both. Smart only chooses which concrete mode the eight
consumer files (or the displayed Theme) render.

## Rule

For an image source, Pillow decodes the image and converts it to 8-bit sRGB (`RGB`). Every channel
is linearized with the sRGB transfer function:

```text
lin(c) = c / 12.92                         if c <= 0.04045
lin(c) = ((c + 0.055) / 1.055) ** 2.4      otherwise
```

where `c` is `byte / 255`. The mean relative luminance is the average of every linearized channel
over every pixel:

```text
L = mean( (lin(R) + lin(G) + lin(B)) / 3 )
```

Black is `0`, white is `1`, and a gray with linear value `0.5` (sRGB byte 188, about `#bcbcbc`)
measures `0.5`. For a color source the seed color's three channels use the same formula. The CLI's
primary source is an image.

The decision is:

```text
mode = light  if L >= smart_threshold
mode = dark   otherwise
```

The average is a simple mean of the linearized channels, not WCAG's `0.2126 R + 0.7152 G +
0.0722 B` weighting. This is the formula the ticket defines and the one the tests pin.

## Configuration

| Layer | Key | Default |
| --- | --- | --- |
| Settings | `[output] default_mode = "dark" \| "light" \| "smart"` | `dark` |
| Settings | `[output] smart_threshold = <0..1>` | `0.5` |
| Environment | `THEME__OUTPUT__DEFAULT_MODE` | from settings |
| Environment | `THEME__OUTPUT__SMART_THRESHOLD` | from settings |
| CLI | `--mode dark\|light\|smart` | `output.default_mode` |
| CLI | `--smart-threshold <0..1>` | `output.smart_threshold` |

`--mode` and `--smart-threshold` override their settings values for that invocation. An invalid
threshold (not a finite number in `[0, 1]`) is rejected with `InvalidSmartThresholdError`;
`dump-config` serializes both fields and `info` reports them under `settings.output`.

## Resolution point

Smart is resolved **before** the processor request is built. Local rendering uses the concrete mode
directly, the container inner command receives `--mode dark` or `--mode light` (never `smart`), and
`--dry-run` prints the resolved concrete mode. The engine and the catalog are unchanged.

## Not matugen's smart mode

matugen has its own `--mode smart` for color generation. It is not used here: on the real wallpaper
corpus it picked `dark` for every image, including bright synthetic images (see the probe recorded
on `REQ-018`). `tpr --mode smart` is independent of the engine and of matugen's choice; it is a
deterministic luminance-threshold policy over the source.

`scheme-smart` remains a matugen/native engine parameter concern. It is unrelated to projection
`--mode smart`.

## Evidence

- `tests/unit/domain/test_smart_mode.py` — white ≈ 1, black ≈ 0, sRGB 188 ≈ 0.5 linear, bright → light,
  dark → dark, and mean ≈ 0.6 flips light → dark at threshold `0.8`.
- `tests/unit/cli/test_generate.py` / `test_show.py` — CLI smart mode, settings default, threshold
  flip, invalid threshold, dry-run and container concrete mode.
- `tests/unit/adapters/settings/*` — defaults, choices, range validation, env/CLI overrides.

Verify:

```bash
cd .
uv run pytest -q tests/unit/domain/test_smart_mode.py tests/unit/cli/test_generate.py
make gates
```

## Validation (2026-10-28)

| Source | Mean relative luminance | Threshold | Selected |
|---|---:|---:|---|
| bright gradient | 0.7404 | 0.5 | light |
| bright gradient | 0.7404 | 0.9 | dark |
| windows-95-dark | 0.1845 | 0.5 | dark |
| zenitsu-agatsuma | 0.0171 | 0.5 | dark |

- `default_mode = "smart"` in settings → `generate` with no `--mode` selects light for the bright
  gradient.
- `THEME__OUTPUT__SMART_THRESHOLD=0.9` flips the bright gradient to dark.
- The selected mode's `colors.yaml` surface matches `theme.json.modes.<mode>`; container mode
  receives the concrete `dark`/`light` and writes the same nine files.
