---
title: "Theme Producer — architecture spine"
status: draft
created: 2026-10-27
updated: 2026-10-27
source: spec-theme-producer
---

# Theme Producer — architecture spine

Only the decisions that keep independently built parts consistent. Everything else is a build
ticket's call.

## AD-1 — Theme is the root domain object; 16 colors are a projection

`Theme` = source + scheme + contrast + `dark`/`light` modes, each mode carrying the 50 Material
roles and six tonal palettes. The 16-color ANSI set is a projection, not the model.

Why: CSG's 16-slot model (`domain/models.py:43-57`) is the ceiling this project exists to remove;
GTK/Adwaita/icons/btop already want names, and the icon vocabulary expects `surface`/`accent`/
`accent-muted` (`dotfiles-assets/icons/mappings/defaults.yaml:16-18`).

Verify: `pytest tests/unit/domain -q`; golden Theme fixture with 50 roles + 6×18 tones.

## AD-2 — Two axes: source extraction vs scheme/projection

The engine produces a Theme from a source; projections render it. "Backend" (CSG's word) is split
into **source** (image/color/json), **engine** (matugen/native), and **projection** (per consumer).

Why: CSG's `Backend` conflates extraction with output model; Material is not an extraction
algorithm.

Verify: `tpr list-engines` and projection tests are independent of engine tests.

## AD-3 — matugen is the v1 engine, as an external process only

Invocation contract:

```
matugen image <path> --json hex --dry-run --mode <mode> --type <scheme>
        --contrast <float> --source-color-index <0-3> --base16-backend wal
        --config <minimal temp config> --quiet
```

Parse `colors` + `palettes`; both modes are present in one response. Never link, import, or copy
matugen code; never use its templates/hooks/wallpaper/config. Always pass an isolated `-c` config and
a source-color selector (non-TTY fails otherwise).

Why: matugen 4.2.0 emits exactly the Theme model (50 roles, 6×18 palettes, light+dark) via
`--json`; probe evidence in the brief. GPL-2.0-or-later is contained by the process boundary.

Verify: adapter test with a recorded golden JSON; container smoke run; `tpr show` works without a
TTY.

## AD-4 — v2 engine is our own Rust helper on `material-colors`; no v3

A small Rust binary (~200–400 LOC) using the MIT/Apache-2.0 `material-colors` 0.4.x crate emits
`theme.json`-shaped data. matugen becomes a dev-only oracle. A pure-Python engine is a **non-goal**
with revisit triggers: native arm64 without a Rust matrix, single-wheel packaging, Rust maintenance
burden, crate abandonment.

Why: matugen's color engine is the `material-colors` crate (9.8k LOC, MIT/Apache); matugen's own
glue is ~1.6k LOC. Owning the wrapper avoids GPL without porting the algorithms.

Verify: `pytest tests/contract -q -k engine_parity` against the matugen corpus (tolerance recorded
in the ticket); `cargo build` in the engine image.

## AD-5 — Projections are pure and declarative

Each projection is a pure function of `Theme`, with a declared capability: `open` (all roles) or
`fixed` (a mapping table). Mapping tables are contract data with golden tests. A projection never
reads another projection.

Why: prevents the CSG failure mode where template logic silently becomes the model; makes the
consumer switch mechanical.

Verify: golden tests per projection; a mutation test proves only dependent projections change.

## AD-6 — The ANSI projection is its own algorithm

Hue-anchored (red/green/yellow/blue/magenta/cyan) with theme-derived tone/chroma; color0/7 track
surface/on_surface, color8 outline, 9–15 bright variants. Not base16 order, not a luminance ramp.

Why: CSG's ramp makes `color1` not red and `color4` not blue (`pywal_generator.py:82`,
`colors.btop.theme.j2:25-26`); matugen's base16 accents collapse on low-chroma images (probe:
eight identical `#111017` accents).

Verify: hue-window assertions for the six slots; `colors.kitty` and `colors.sequences` generated
from the same table.

## AD-7 — Settings via `config-assembler-engine`; catalogs via the same pipeline

`settings.toml` uses the full 5-strategy chain with OverrideRules; `engines.yaml` uses the same
pipeline with a Pydantic schema; the templates directory uses `CompositePathResolver` only.
`--param` bypasses the assembler and goes through `PydanticTypeCoercer` + `ParameterResolutionService`.

Why: CSG's use is correct and tool-agnostic (`config_resolver.py:73-128`,
`yaml_backend_catalog_loader.py:73-108`, `template_dir_resolver.py:20-37`).

Verify: strategy-chain tests; hermetic canary; `tpr info` prints resolved path + applied overrides.

## AD-8 — One pinned image per engine; tag is the pin

Base image + `Dockerfile.<engine>` via `oci-runtime`; repository root is the build context; image
reference `<prefix>-<engine>-<engine>:<tag>`; `install`/`uninstall` manage them. The matugen image
pins the 4.2.0 release **and its checksum**; the Rust image pins the crate and toolchain.

Why: CSG AD-5/AD-7; reproducible engine behavior; GPL isolation.

Verify: `make image` at `v<version>`; `podman run --rm <base> tpr version`; `tpr install --dry-run`.

## AD-9 — Artifact contract: canonical theme.json + eight drop-in projections

`theme.json` is the public canonical artifact; the eight consumer filenames keep their existing
names and gain semantic tokens additively. No ninth artifact and no `contracts` dependency in v1;
`cli-invocation-contract` adoption is a later ticket once the artifact set is stable.

Why: `contracts/schemas/meta.schema.json:29-70` freezes exactly eight artifact keys; changing the
count is a contracts release and a runtime change. Additive content is contract-safe.

Verify: schema validation; projection filenames match the contract record; adoption spike report.

## AD-10 — License posture

Project MIT. matugen used only as a separate process; distributed images carry its GPL text and
source reference. No matugen templates/config copied. `material-colors` notices carried by the v2
engine. Generated colors are output data.

Why: GPL-2.0-or-later on matugen; MIT/Apache-2.0 on the crate.

Verify: `make docs-check` asserts license/notice files; image labels include the source reference.

## AD-11 — Generation identity for cache invalidation

The Theme records source hash, engine, engine version, scheme, contrast, mode, and template-set
hash. The runtime adapter (later) uses these to derive its cache key; the current runtime key omits
them (`hashing.py:261-279`).

Why: switching engine/settings must not silently return a stale palette.

Verify: `theme.json` contains the identity fields; adoption spike maps them to the runtime hash.

## AD-12 — Hermetic gates and CI parity

`make gates` = test, lint, hermetic, lock-check, docs-check; CI one job per gate plus parity; image
build is a declared CI-only job.

Why: CSG's harness caught real host-leak bugs; hermetic tests are the precondition for trusting
golden projections.

Verify: `make gates`, `make ci-gates-parity`, `make image`.

## AD-13 — CSG and the dotfiles are untouched

No edits to `color-scheme-generator` or the dotfiles tree from this repo. Adoption happens only
after `spike-001-dotfiles-fit` reports and a separate adoption ticket is approved.

Why: two simultaneous migrations (producer + contract/consumers) is the failure mode to avoid.

Verify: `git -C ../dotfiles status --porcelain` empty; adoption ticket links the spike.

## Deliberately left open

- Exact role vocabulary beyond the stable eight aliases (decided in the projections ticket).
- ANSI hue windows and chroma/tone heuristics (decided by the ANSI recipe ticket).
- Whether `theme.json` is emitted as JSON only or JSON + YAML (default JSON).
- The Rust helper's crate version (0.4.x for matugen parity vs 0.5.x for newer spec).
- Whether `theme.html` ships in the wheel or is dev-only.
