---
title: "Theme Producer — spec"
status: draft
created: 2026-10-27
updated: 2026-10-27
source: brief-theme-producer
---

# Theme Producer — spec

## Why

Give the dotfiles tree a theme producer whose root object is a Material You Theme (semantic roles +
tonal palettes + light/dark), with deliberate projections for each consumer and a 16-color ANSI only
where the format requires it.

## Capabilities

### CAP-001 — Theme domain model

The system SHALL represent a `Theme` as immutable domain data: source (kind/path/hash), scheme name,
contrast, and `dark`/`light` modes. Each mode SHALL carry the 50 Material roles and six tonal
palettes (18 tones each), plus generator metadata (engine, engine version, schema version).

Acceptance: unit tests construct a Theme from a golden JSON fixture and assert role/palette counts;
an invalid role name or hex fails validation.
Source: brief §Solution; matugen 4.2.0 probe (`colors` 50, `palettes` 6×18).

### CAP-002 — Source extraction

The system SHALL accept an image path, a seed color, or an imported JSON as the source and produce a
Theme through the configured engine. Non-interactive operation SHALL be deterministic (no prompt).

Acceptance: `tpr generate <image> --engine matugen` succeeds without a TTY; a seed-color run and a
JSON-source run produce a Theme; missing/invalid source exits non-zero with a typed error.
Source: matugen CLI (`--source-color-index`, `image|color|json` subcommands).

### CAP-003 — Engine port and catalog

Color generation SHALL sit behind `ThemeEnginePort`. The active engine SHALL be resolvable from
`engines.yaml` through `config-assembler-engine`, with per-engine parameters (`mode`, `scheme_type`,
`contrast`, `source_color_index`, `timeout`) validated by choices and resolved through the domain
parameter service.

Acceptance: `tpr list-engines` reports availability; `--engine <name>` selects it; an unknown
engine or param exits non-zero with a resolution error.
Source: CSG `backends.yaml` pattern (`adapters/yaml_backend_catalog_loader.py`).

### CAP-004 — Settings resolution

The system SHALL resolve settings with the CSG-proven chain: CLI path > env path > directory
traversal > XDG > packaged default, via `config-assembler-engine`; templates SHALL resolve through
`CompositePathResolver` only.

Acceptance: tests cover all five strategies and env overrides; a stray host `settings.toml` cannot
change a hermetic run.
Source: `config-assembler-engine` README; CSG `assembled_config_resolver.py`.

### CAP-005 — Canonical theme artifact

The system SHALL write a versioned `theme.json` containing source, scheme, contrast, generator and
both modes (roles + palettes).

Acceptance: `theme.json` validates against the committed schema; every role referenced by any
projection exists in it.
Source: brief §Solution; matugen `--json` shape.

### CAP-006 — Projections

The system SHALL render the Theme to: `colors.gtk.css`, `colors.adw.css`, `colors.yaml`,
`colors.rasi`, `colors.btop.theme`, `colors.conf`, `colors.kitty`, `colors.sequences`, and a
dev-only `theme.html`. Projections SHALL be pure functions of the Theme and SHALL NOT read each
other.

Acceptance: each projection has a golden test; a mutation to a Theme role changes every projection
that references it and no others.
Source: dotfiles consumer table (`consumer_path_spec.py:49-56`, `itr_adapter.py:346-403`,
`colors.btop.theme.j2`).

### CAP-007 — Semantic vocabulary and compatibility aliases

Every projection that can carry named tokens SHALL emit the stable vocabulary (`background`,
`foreground`, `accent`, `accent-muted`, `surface`, `on_surface`, `error`, `warning`) plus the legacy
positional aliases (`color0..15`, `color_00..15`) where the format allows.

Acceptance: `colors.yaml` contains all vocabulary keys and the legacy list; `colors.gtk.css` contains
the semantic names and `color_00..15`; `colors.rasi` contains both.
Source: icon defaults (`dotfiles-assets/icons/mappings/defaults.yaml:16-18`); ITR extra-key
preservation (`file_color_scheme_loader.py:78-83`).

### CAP-008 — ANSI intent projection

The 16-color projection SHALL be a deliberate ANSI palette (hue-anchored red/green/yellow/blue/
magenta/cyan, surface/on-surface for 0/7, outline for 8, bright variants for 9–15), not a luminance
ramp.

Acceptance: the six hue slots fall within documented hue windows; color0/7 track surface/on_surface;
the same projection feeds `colors.kitty` and `colors.sequences`.
Source: kitty color table (color0..255); brief §Problem (CSG ramp).

### CAP-009 — Container images and verbs

The system SHALL build one pinned base image plus one image per engine through `oci-runtime`, with the
image tag as the pin; `install`, `uninstall` and `list-engines` SHALL manage them.

Acceptance: `make image` builds at `v<version>` and runs `tpr version` in the base image;
`tpr install` builds the base + selected engines; `tpr uninstall` removes them.
Source: CSG `install_cmd.py`, `container_processor.py:66-71`, `Makefile`.

### CAP-010 — CLI surface

The system SHALL expose `generate`, `show`, `list-engines`, `install`, `uninstall`, `info`,
`dump-config`, `dump-templates`, `version`, and `--version`, with `--output-format json|rich|plain`,
`--runtime local|container`, `--engine`, `--param`, `--templates-dir`, `--config`, `--dry-run`.

Acceptance: CLI tests cover every verb and the global flags; JSON is the default output.
Source: CSG CLI surface; `cli-output` adapters.

### CAP-011 — Dotfiles adoption seam

The system SHALL keep the eight consumer filenames and a canonical `theme.json`, and SHALL expose a
generation identity (source hash, engine, engine version, scheme, contrast, mode, template set) so
the runtime can invalidate caches deterministically when the producer or settings change.

Acceptance: a spike reports the runtime adapter shape and the exact artifact/hash changes; no
dotfiles edits are made by this repo.
Source: `dotfiles-runtime/.../hashing.py:261-279`; `contracts/schemas/meta.schema.json:29-70`.

### CAP-012 — Evidence and gates

The system SHALL keep the suite hermetic and gate every ticket with `make gates`; CI SHALL run one
job per gate plus parity.

Acceptance: `make gates` and `make ci-gates-parity` exit 0 on a fresh clone with empty HOME/XDG.
Source: CSG `Makefile`, `.github/workflows/gates.yml`, `tests/conftest.py`.

## Constraints

- MIT project; matugen only as a separate process; no GPL code copied.
- Sibling dependencies pinned as git tags, never paths/editable.
- `theme.json` and the projection catalog are public asset surfaces (schema/version discipline).
- CSG is untouched; dotfiles are untouched until the adoption ticket.

## Non-goals

- A pure-Python color engine (revisit only on a recorded trigger).
- matugen's template engine, wallpaper setting, hooks, or config format.
- GUI, runtime light/dark switching, PyPI publishing.

## Success signal

A generated template directory is a complete, schema-valid theme; every consumer can read semantic
tokens where its format allows; terminals get an intentional ANSI palette; the gates are green; the
later adoption spike shows CSG can be replaced without an unversioned contract break.
