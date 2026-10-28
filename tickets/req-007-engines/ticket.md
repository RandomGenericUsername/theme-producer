---
id: REQ-007
title: "ThemeEnginePort + matugen engine + engines.yaml"
kind: requirement
status: proposed
lane: 3 — ticket-multi
parent: EPIC-001
links:
  openspec: req-007-engines
  bmad: none
worktree: none
branch: none
---

# ThemeEnginePort + matugen engine + engines.yaml

## Requirement

Implement the engine port and the v1 matugen adapter, with the engine catalog and parameter
resolution. matugen is an external process only; no code is linked, imported, or copied.

## Acceptance

- [ ] `ThemeEnginePort` (available/generate) and `EngineConfig`; `--engine matugen` selects it.
- [ ] `engines.yaml` catalog (mode, scheme_type, contrast, source_color_index, timeout) resolved
      through `config-assembler-engine`; `--param` coerced via `PydanticTypeCoercer` and resolved via
      `ParameterResolutionService`.
- [ ] Invocation exactly AD-3: `--json hex --dry-run`, isolated temp `-c`, always a source-color
      selector, `--quiet`; no host config, no templates, no hooks, no wallpaper.
- [ ] Parser reads `colors` + `palettes`, both modes; handles 6/8-digit hex; typed errors for
      non-zero exit, timeout, malformed JSON, missing binary.
- [ ] Golden matugen JSON fixture drives unit tests; a non-TTY integration test proves no prompt.
- [ ] `make gates` green.

## Done-when

`pytest tests/unit/adapters/engines tests/integration/test_matugen -q` green; no-TTY run succeeds.

