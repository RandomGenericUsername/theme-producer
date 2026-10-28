---
id: REQ-006
title: "Settings via config-assembler-engine"
kind: requirement
status: proposed
lane: 2 — openspec-single
parent: EPIC-001
links:
  openspec: req-006-settings
  bmad: none
worktree: none
branch: none
---

# Settings via config-assembler-engine

## Requirement

Wire `config-assembler-engine` exactly as CSG does: a 5-strategy chain for `settings.toml`, a
Pydantic boundary schema, OverrideRules for every scalar override, and a path-only resolver for the
templates directory.

## Acceptance

- [ ] Env prefix `THEME`; XDG subdir `theme-producer`; file `settings.toml`; templates env
      `THEME_TEMPLATES_TEMPLATES_DIR`.
- [ ] Chain: CLI > ENV path > traversal (3 levels) > XDG > packaged default.
- [ ] OverrideRules for output, generation, runtime, container and templates keys; `--param`
      bypasses the assembler (REQ-007 owns coercion).
- [ ] `tpr info` (or an internal resolver API) reports resolved path + applied overrides.
- [ ] Tests cover all five strategies, env overrides, malformed TOML, invalid enum values.
- [ ] Hermetic canary still green; a host `settings.toml` cannot leak in.

## Done-when

`pytest tests/unit/adapters/settings -q` green and `make hermetic` green.

