# Changelog

## Unreleased — `on_backdrop` (REQ-022)

- **Produced role `on_backdrop`** (additive, `theme.json` schema `1.1`): the
  ink that reads over the wallpaper's top bar band. The engine still emits
  exactly 50 Material roles; `tpr` measures the top `min(48, height)` rows
  (resized to ≤64 px wide, mean WCAG relative luminance) and selects the
  max-contrast neutral-pole role per mode, with `on_surface` as the tie winner.
  Best effort below WCAG 4.5. Seed-color and imported-JSON themes fall back to
  `on_backdrop = on_surface`. Emitted by `theme.json`, `colors.yaml`,
  `colors.gtk.css`, `colors.adw.css`, `colors.rasi`, and `colors.conf`; ANSI,
  kitty, sequences, and btop are unchanged. See `docs/VOCABULARY.md`.

## 0.4.0 — 2026-10-28

- **Configurable scheme policy (`scheme-smart`)**: a hexagonal `tpr` feature that picks one of the
  nine Material variants from image metrics, for both engines.
  - Metrics: saturation, Hasler–Süsstrunk colorfulness, relative lightness, contrast,
    saturation-weighted hue diversity (256×256 Triangle, Pillow).
  - Ordered ANDed rules, first match, per-policy default; nine real variants; no arbitrary code.
  - `[generation] scheme_type` (default `scheme-tonal-spot`) and `scheme_policy` (default
    `balanced`); `--param scheme_type=scheme-smart`, `--scheme-policy`, `--policies-file`, env
    overrides. `scheme_policy` alone does not enable smart; only `scheme-smart` does.
  - User catalog: `scheme-policies.yaml` via `config-assembler-engine` (CLI → env → traversal →
    XDG → packaged default); profiles `balanced`, `vivid`, `muted`, `source-faithful`.
  - Resolved on the host; containers receive the concrete variant; `theme.json.scheme` is concrete;
    `--dry-run` shows metrics/profile/variant.
  - Corpus-calibrated: `balanced` vibrant gate `colorfulness>=0.18, saturation>=0.45`; `vivid`
    neutral gate; `muted` tonal-spot gate. Seven-wallpaper table in `docs/SCHEME-POLICY.md`.

## 0.3.1 — 2026-10-28

- **Legacy token compatibility (`BUG-003`):** `colors.gtk.css` now emits
  `color_background`, `color_foreground`, `color_cursor` alongside `color_00..15`; `colors.rasi`
  emits zero-padded `color00..15` (rofi uses `@color04`/`@color01`/`@color07`/`@color10`).
  AGS/rofi compatibility test pins both sets; every other projection byte is unchanged.
- **Consumer capability audit:** `docs/CONSUMER-AUDIT-2026-10-28.md` maps every artifact to its
  consumers, token usage, format capability and migration order (read-only; no dotfiles edits).

## 0.3.0 — 2026-10-28

- **Configurable smart projection mode (`REQ-018`):** `--mode smart` selects light/dark from the
  source image's mean relative luminance (Pillow, sRGB-linearized), threshold 0.5 by default.
  `[output] default_mode` and `[output] smart_threshold` are configurable; `--smart-threshold` and
  `THEME__OUTPUT__SMART_THRESHOLD` override; container/dry-run receive the concrete mode.
- Dark remains the default; `theme.json` still carries both modes; no artifact changes.
- Smart is `tpr`'s explicit luminance rule, not matugen's `--mode smart` (which picked dark on the
  real corpus).

## 0.2.0 — 2026-10-28

Engine-completion release: native now exposes matugen's source/lightness controls, and projections
can render light mode.

### Added

- `prefer` (`darkness`, `lightness`, `saturation`, `less-saturation`, `value`,
  `closest-to-fallback`) and `fallback_color` on both engines (`REQ-015`).
- `lightness_dark` / `lightness_light` on both engines (`REQ-016`). The native transform uses HSI
  intensity (mean gamma-encoded sRGB) and matugen's truncation; oracle parity is 2489/2500 roles
  exact and 2500/2500 within ±1.
- `--mode dark|light` on `generate`/`show` (`REQ-017`): the same eight consumer filenames render the
  selected mode; `theme.json` still carries both; dark output is byte-identical to 0.1.0.
- `--mode smart` on `generate`/`show` (`REQ-018`): resolves to `light` when the source's mean
  relative luminance is at least the threshold, otherwise `dark`. Configurable with
  `[output] default_mode` / `smart_threshold`, `THEME__OUTPUT__*`, and `--smart-threshold`; smart is
  resolved before the container invocation and dry-run prints the concrete mode. Pillow is a
  runtime dependency for image luminance. See `docs/SMART-MODE.md`.
- Native extraction moved to 112×112 Triangle to match matugen's observed candidate list; default
  source-color parity improved from 1/7 to 6/7 real wallpapers.

### Known limitations

- Native image-source selection still diverges from matugen on some wallpapers (zenitsu/yasuke)
  because matugen 4.2.0 vendors its own `material-colors` fork. 41/56 oracle pairs are exact or ±1;
  the rest are pinned as known divergences. Use `engine = "matugen"` for exact visuals.
- `scheme-smart` is not implemented in native (it is not advertised); `--mode smart` is an
  independent `tpr` projection policy. Runtime light/dark switching is not wired (the producer can
  render either mode, the runtime still consumes the dark set).
- `theme.json` carries both modes; only the eight consumer files are mode-selected.

## 0.1.0 — 2026-10-27

First release. The theme producer turns a wallpaper (or a seed color) into a Material You
**Theme** and renders it to consumer projections.

### Added

- **Theme domain** — 50 Material roles, six tonal palettes × 18 tones, dark and light modes,
  source/generator metadata, the stable alias vocabulary (`background`, `foreground`, `accent`,
  `accent-muted`, `surface`, `on_surface`, `error`, `warning`) and the legacy `color0..15` indices.
- **Canonical `theme.json`** — versioned JSON Schema and a strict writer/round-trip.
- **Settings** — `config-assembler-engine` five-strategy chain (`THEME` prefix), Pydantic boundary,
  OverrideRules, and a path-only templates resolver.
- **Engines behind `ThemeEnginePort`**
  - `matugen` 4.2.0: pinned external process, `--json hex --dry-run`, isolated config, no templates
    or hooks; GPL-2.0-or-later used only across a process boundary with license/source notice.
  - `native`: our own Rust helper on the MIT/Apache-2.0 `material-colors` 0.4.2 crate. Exact parity
    with matugen on a shared seed color (50 roles + 108 tones, zero deltas).
- **Projections** — `colors.gtk.css`, `colors.adw.css`, `colors.yaml`, `colors.rasi`,
  `colors.conf`, `colors.btop.theme` (explicit 48-key table), `theme.html` preview, plus a
  deliberate ANSI intent projection for `colors.kitty` and `colors.sequences` (hue-anchored, not a
  luminance ramp).
- **CLI** — `generate`, `show`, `list-engines`, `install`, `uninstall`, `info`, `dump-config`,
  `dump-templates`, `version`, `--version`; JSON/rich/plain output; `--param` coercion; local,
  container and dry-run processors.
- **Container images** — pinned base + matugen + native; checksummed matugen release; GPL notice
  and source reference; `make image` smoke-runs all three.
- **Harness** — mu/CSG ticket system, OpenSpec config, BMAD routing, worktree guard, hermetic tests,
  gates and CI gate parity.

### Fixed

- The native catalog no longer advertises `scheme-smart` (the helper implements the nine real
  Material variants; matugen keeps ten).
- The default container image tag resolves to `v<package version>` instead of `latest`.

### Known follow-ups

- `REQ-012` — the `tpr` record in the `contracts` repo and its conformance test (cross-repo release).
- `REQ-014` — dotfiles runtime/provisioning adoption (separate repo, after a released tag).
