# tpr-native

The v2 color engine for theme-producer: a small Rust helper that turns one
source (an image or a `#rrggbb` seed) into the canonical `theme.json` shape on
stdout. It is original code that uses the MIT/Apache-2.0
[`material-colors`](https://crates.io/crates/material-colors/0.4.2) crate; no
matugen code is copied, imported, or linked.

## Build

```sh
cd native
cargo build --release --locked
./target/release/tpr-native --version   # 0.1.0
```

The crate version is pinned in `Cargo.toml` and `Cargo.lock`; the `native`
container image builds the same lockfile in a `rust:1.99-slim` stage.

## Usage

```text
tpr-native (--image <path> | --color <#rrggbb>)
           [--scheme <scheme>] [--contrast <float>]
           [--lightness-dark <float>] [--lightness-light <float>]
           [--source-color-index <int>] [--json]
           [--version]
```

- `--image` / `--color`: exactly one source.
- `--scheme`: one of `scheme-tonal-spot`, `scheme-content`,
  `scheme-expressive`, `scheme-fidelity`, `scheme-fruit-salad`,
  `scheme-monochrome`, `scheme-neutral`, `scheme-rainbow`, `scheme-vibrant`.
  Defaults to `scheme-tonal-spot`. `scheme-smart` is a matugen-only mode: it is
  not in the native catalog, so the CLI rejects it during `--param` validation,
  and a direct helper invocation fails with a clear error instead of guessing.
- `--contrast`: `-1..1`, default `0`. The value is passed to
  `DynamicScheme::by_variant(..., Some(contrast))`.
- `--lightness-dark` / `--lightness-light`: `-1..1`, default `0`, applied after
  scheme generation to every role in the corresponding mode (out-of-range
  values are clamped). See [Lightness controls](#lightness-controls).
- `--source-color-index`: image only, default `0`, clamped to the ranked list
  (0..4 when the image yields that many suitable colors).
- `--json`: always emits JSON on stdout; accepted for compatibility.

## Lightness controls

matugen 4.2.0 exposes `--lightness-dark` / `--lightness-light`; `tpr-native`
reproduces them. The transformed scalar was identified by oracle probing (five
seeds, both modes, `-1, -0.5, 0, 0.5, 1`, all 50 roles) — not by reading
matugen's GPL source: it is the **mean of the gamma-encoded sRGB channels**
(HSI intensity, `(r + g + b) / 3` in `0..1`), not HCT tone or CIE L*.

* dark: `target = argument + (1 - argument) * intensity` — lightness 1 stays at
  1, 0 moves to `argument`.
* light: `target = (1 + argument) * intensity` — lightness 0 stays at 0, 1
  moves to `1 + argument`.

Each sRGB channel is then scaled by `target / intensity`, clamped to
`0..=255`, and truncated to `u8` exactly like matugen. An all-black color has no
intensity and is left unchanged; `source_color` is echoed verbatim; tonal
palettes are not transformed. `tests/contract/test_native_lightness.py` pins
this against the oracle: 2489/2500 role comparisons are byte-exact and the
remaining 11 differ by one unit (matugen's float32 rounding).

## Output

Both modes are always emitted: 50 Material roles (including `source_color` and
the theme's `background`/`on_background`) and six tonal palettes with the 18
canonical tones each. Colors are lowercase `#rrggbb`.

```json
{
  "schema_version": "1.1",
  "generator": {"engine": "native", "engine_version": "0.1.0", "schema_version": "1.1"},
  "source": {"kind": "color", "path": null, "hash": "..."},
  "scheme": "scheme-tonal-spot",
  "contrast": 0.0,
  "modes": {"dark": {"roles": {}, "palettes": {}}, "light": {"roles": {}, "palettes": {}}}
}
```

The helper emits the 50 engine roles only. The Python producer adds the
produced `on_backdrop` role to each mode after the engine returns; see
`docs/VOCABULARY.md`.
Images are decoded once, resized to 128×128 with Lanczos3, quantized with
`QuantizerCelebi`, and ranked with `Score`; the seed is the selected ranked
color. The SHA-256 hash is computed over the file bytes exactly as read. For a
color seed the hash is the adapter's SHA-256 of the color string.

## Parity and licensing

With matugen 4.2.0 and `tpr-native` both on `PATH`,
`uv run pytest tests/contract/test_engine_parity.py -q -rs` compares all 50
roles and all 18 tones in both modes. The engines share the `material-colors`
generator, so the comparison is exact at the default tonal-spot scheme.

Third-party notices for `material-colors` and the direct dependencies are in
[`../THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md) and ship in the
image under `/usr/share/doc/tpr-native/`.
