# Handoff — v0.1.0

Date: 2026-10-27
Repo: `/home/inumaki/Development/theme-producer`
Tag: `v0.1.0`
Branch: `master`

## What exists

`tpr` turns a wallpaper (or a seed color) into a Material You Theme and renders it to the
consumer projections. The root object is `Theme` (50 roles + six tonal palettes × 18 tones +
dark/light), not a 16-color palette.

```
src/theme_producer/
  domain/        Theme, Color, roles, palettes, aliases, ANSI recipe
  ports/         ThemeEnginePort, ProjectionPort, processor, output, container runtime
  adapters/
    engines/     matugen (v1, external process), native (v2, Rust helper)
    projections/ registry, btop mapping, ANSI
    settings/    config-assembler-engine chain
    output/      cli-output JSON/rich/plain
    docker/      Dockerfile.base, Dockerfile.matugen, Dockerfile.native
  defaults/      settings.toml, engines.yaml, templates/*.j2
  cli/           generate, show, list-engines, install, uninstall, info, dump-config,
                 dump-templates, version
native/          Rust helper on material-colors 0.4.2 (MIT/Apache-2.0)
```

Artifacts produced by `tpr generate`:

```
theme.json              canonical Theme (versioned schema)
colors.gtk.css          semantic roles + legacy color_00..15
colors.adw.css          libadwaita named colors + CSS custom properties
colors.yaml             aliases + all roles + legacy 16 list (ITR)
colors.rasi             semantic variables + legacy color0..15
colors.conf             hyprland variables + legacy aliases
colors.btop.theme       explicit 48-key btop mapping
colors.kitty            ANSI intent (16) + bg/fg/cursor/selection
colors.sequences        OSC 4/10/11/12 ANSI sequences
theme.html              dev-only preview
```

## Evidence

| Check | Result |
|---|---|
| `make gates` | 330 passed, 8 skipped; ruff clean; hermetic run clean; lock-check clean |
| `make build` | sdist + wheel for 0.1.0 |
| `make image IMAGE_ENGINE=podman` | base 341 MB, matugen 353 MB, native 344 MB; all smoke-run |
| `tpr generate` (matugen) | 9 files, exit 0 |
| `tpr generate` (native) | 9 files, exit 0 |
| `tpr generate --runtime container --engine native` | 9 files, exit 0 (15.2 s) |
| `tpr install --dry-run` | `v0.1.0` images, no `latest` |
| Seed parity (matugen vs native) | 50 roles + 108 tones, **0 deltas** at contrast 0 and 0.5 |
| Image-source parity | 56/316 values differ by ±1 (rounding); acceptable, seed parity is exact |
| `make ci-gates-parity` | exit 0 |

## Cross-repo follow-ups (blocked, by design)

1. **REQ-012 — contracts record.** Add the `tpr` record to the `contracts` repo
   (`cli-invocation-contract`): argv, env (`THEME__OUTPUT__DIRECTORY`, `THEME__OUTPUT__OVERWRITE`),
   the 9 artifact names (8 consumers + `theme.json`), exit codes, timeout. Release a contracts tag,
   then pin it here and add `tests/contract/test_invocation_contract.py`.
2. **REQ-014 — dotfiles adoption.** `tickets/spike-001-dotfiles-fit/ticket.md` has the full report.
   Short version:
   - Add a sibling `IColorSchemeGenerator` adapter; do not make `CsgAdapter` configurable.
   - Stop `derive.ensure_palette` hardcoding `csg_templates`; give the producer an inputs hash.
   - Put a producer/engine/settings fingerprint into `palette_entry_hash` and
     `invalidation.recomputed()`, or a producer switch silently reuses the old palette.
   - Keep the 8 consumer filenames; keep `theme.json` producer-side unless the meta schema is
     versioned.
   - Add a producer selector (e.g. `RUNTIME__PALETTE__PRODUCER=csg|tpr`) with `csg` default.
   - Rollback to CSG is safe only with the fingerprint in the key; otherwise evict
     `cache/palettes/<ph>` and the cascaded icons.
   - Provisioning: cli-tools pin/build, `tpr-settings.toml.j2`, verify image list, assets pin.
   - AGS appearance hash and ITR `colors.yaml` chaining are the two cascade points.

## Commands

```bash
cd /home/inumaki/Development/theme-producer
make sync
make gates
make image IMAGE_ENGINE=podman
uv run tpr generate wallpaper.png -o /tmp/theme
uv run tpr --output-format json list-engines
```

In the container images:

```bash
podman run --rm tpr-matugen-podman:v0.1.0 matugen --version    # 4.2.0
podman run --rm tpr-native-podman:v0.1.0 tpr-native --version  # 0.1.0
```

## Notes

- matugen is GPL-2.0-or-later and is used only as a separate process; images carry
  `/usr/share/doc/matugen/LICENSE` and `SOURCE`. The native helper carries
  `THIRD_PARTY_LICENSES.md`.
- `REQ-012` and `REQ-014` are the only open tickets; the epic remains `in-progress`.
