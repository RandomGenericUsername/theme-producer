# theme-producer (`tpr`)

A theme producer for the dotfiles CLI toolchain. It turns a wallpaper image (or a seed color) into
a **Theme** — Material You semantic roles, tonal palettes, light and dark — and renders that Theme
through a bundled catalog of projections for the consumers in the dotfiles tree.

This is the successor to `color-scheme-generator` (`csg`). CSG stays untouched and production until
the dotfiles wiring ticket proves this project can replace it. The difference is the model: CSG's
root object is a 16-color palette; this project's root object is a Theme, and the 16-color ANSI set
is one projection among many.

## Status

`v0.4.0`. The Theme model, both engines (matugen and native), the projection catalog, the CLI and
the container images are built and gated. The two remaining tickets are cross-repo:

- `REQ-012` — the `tpr` record in the `contracts` repo and its conformance test.
- `REQ-014` — dotfiles runtime/provisioning adoption.

The ticket tree in `tickets/` is the live plan; `_bmad-output/` holds the brief, spec and
architecture spine.

## Quick start

```bash
make sync
make gates
make image IMAGE_ENGINE=podman          # base + matugen + native at v0.4.0
uv run tpr generate wallpaper.png -o /tmp/theme
uv run tpr generate wallpaper.png --mode smart -o /tmp/theme   # luminance-selected mode
uv run tpr --output-format json list-engines
```

## Shapes

- `theme.json` — canonical, versioned Theme artifact (roles + tonal palettes + both modes).
- Projections — `colors.gtk.css`, `colors.adw.css`, `colors.yaml`, `colors.rasi`,
  `colors.btop.theme`, `colors.conf`, `colors.kitty`, `colors.sequences`, plus a dev-only
  `theme.html` preview.
- Engines behind `ThemeEnginePort` — v1 `matugen` (pinned, containerized, JSON only), v2 own Rust
  helper on the MIT/Apache `material-colors` crate. A pure-Python engine is a recorded non-goal.
- Projection mode — `--mode dark|light|smart` on `generate`/`show`; `smart` picks `light` when the
  source's mean relative luminance is at least `smart_threshold`, otherwise `dark`. Configure with
  `[output] default_mode` / `smart_threshold` or the matching env/CLI overrides. See
  `docs/SMART-MODE.md`.

## Container images

The engine runs in a pinned image; the tag is the pin (never `latest` by default).

| Image | Reference | Contents |
| --- | --- | --- |
| base | `tpr-base-<container-engine>:v<version>` | `python:3.14-slim` + the frozen `uv` env and the `tpr` console script |
| matugen | `tpr-matugen-<container-engine>:v<version>` | base + matugen 4.2.0 (sha256-pinned) with its GPL-2.0-or-later text and source reference under `/usr/share/doc/matugen/` |
| native | `tpr-native-<container-engine>:v<version>` | base + `tpr-native` 0.1.0 built from `native/` on the MIT/Apache-2.0 `material-colors` crate, with third-party notices under `/usr/share/doc/tpr-native/` |

```sh
make image IMAGE_ENGINE=podman        # builds base, matugen, and native at v<pyproject version>
tpr install --container-engine podman # same references, tag resolves to v<version>
podman run --rm tpr-matugen-podman:v0.1.0 matugen --version
podman run --rm tpr-native-podman:v0.1.0 tpr-native --version
```

`make image` is a declared CI-only job (`image`) because it needs a live engine and network access.
An empty `container.image_tag` (the packaged default) resolves to `v<package version>`, so
`tpr install` plans the same tags `make image` builds. Set it explicitly to override the pin.

## Harness

- `tickets/` — epic/req/bug/spike/task/ops items, `INDEX.md`, `LIFECYCLE.md`, router lanes.
- `openspec/` — bounded slices.
- `_bmad-output/theme-producer/` — brief, spec, architecture spine.
- `scripts/worktree-guard.sh` — no-main discipline.
- `make gates` — test, lint, hermetic, lock-check, docs-check; CI parity enforces one job per gate.
