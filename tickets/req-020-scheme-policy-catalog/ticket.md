---
id: REQ-020
title: "Scheme policy catalog + metrics adapters"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-020/
branch: ticket/req-020-scheme-policy-catalog
---

# Scheme policy catalog + metrics adapters

## Requirement

Implement the adapters and configuration for `scheme-smart` per `docs/SCHEME-POLICY.md`:

- `PillowImageMetrics` implementing `ImageMetricsPort`: decode with Pillow, resize to 256×256
  Triangle, compute the five metrics (sRGB-linearized; documented formulas). Color source path.
- `YamlSchemePolicyCatalogLoader` implementing `SchemePolicyCatalogPort` through
  `config-assembler-engine`: five-strategy chain, Pydantic schema, `THEME_SCHEME_POLICIES` prefix,
  XDG `theme-producer/scheme-policies.yaml`, packaged default.
- `src/theme_producer/defaults/scheme-policies.yaml` with `balanced`, `vivid`, `muted`,
  `source-faithful` profiles.
- Settings: `[generation] scheme_policy` (str, default `balanced`), OverrideRules, conversion,
  `defaults/settings.toml`, `dump-config`, `info`.
- CLI: `--scheme-policy <profile>`, `--policies-file <path>` (global or generate/show as designed),
  env `THEME__GENERATION__SCHEME_POLICY`, `THEME_SCHEME_POLICIES_CONFIG_FILE_PATH`.
- No engine/CLI generate wiring yet (REQ-021).

## Acceptance

- [ ] Metrics are deterministic and tested on white/black/colorful/muted synthetic images.
- [ ] Catalog loads through the five strategies; packaged default validates; user override works.
- [ ] Schema rejects unknown metric/operator/variant, bad ranges, empty rules, missing defaults.
- [ ] Settings/env/CLI select a profile and catalog file; `info`/`dump-config` show them.
- [ ] `make gates` green; no engine behavior change yet.

## Evidence

- `docs/SCHEME-POLICY.md` AD-2/AD-4/AD-7.
- Existing `config-assembler-engine` loaders: `adapters/engines_catalog_loader.py`, settings resolver.
