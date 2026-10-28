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
           [--source-color-index <int>] [--json]
           [--version]
```

- `--image` / `--color`: exactly one source.
- `--scheme`: one of `scheme-tonal-spot`, `scheme-content`,
  `scheme-expressive`, `scheme-fidelity`, `scheme-fruit-salad`,
  `scheme-monochrome`, `scheme-neutral`, `scheme-rainbow`, `scheme-vibrant`.
  Defaults to `scheme-tonal-spot`. `scheme-smart` is a matugen-only mode; the
  helper fails with a clear error instead of guessing.
- `--contrast`: `-1..1`, default `0`. The value is passed to
  `DynamicScheme::by_variant(..., Some(contrast))`.
- `--source-color-index`: image only, default `0`, clamped to the ranked list
  (0..4 when the image yields that many suitable colors).
- `--json`: always emits JSON on stdout; accepted for compatibility.

## Output

Both modes are always emitted: 50 Material roles (including `source_color` and
the theme's `background`/`on_background`) and six tonal palettes with the 18
canonical tones each. Colors are lowercase `#rrggbb`.

```json
{
  "schema_version": "1",
  "generator": {"engine": "native", "engine_version": "0.1.0", "schema_version": "1"},
  "source": {"kind": "color", "path": null, "hash": "..."},
  "scheme": "scheme-tonal-spot",
  "contrast": 0.0,
  "modes": {"dark": {"roles": {}, "palettes": {}}, "light": {"roles": {}, "palettes": {}}}
}
```

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
