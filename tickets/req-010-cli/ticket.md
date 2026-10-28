---
id: REQ-010
title: "CLI surface + local/container/dry-run processors"
kind: requirement
status: in-progress
lane: 2 — openspec-single
parent: EPIC-001
links:
  openspec: req-010-cli
  bmad: none
worktree: .worktrees/req-010/
branch: ticket/req-010-cli
---

# CLI surface + local/container/dry-run processors

## Requirement

Expose the CLI and wire the processors behind one port, using `cli-output` for JSON/rich/plain.

## Acceptance

- [ ] Verbs: `generate show list-engines install uninstall info dump-config dump-templates version`
      and `--version`.
- [ ] Global flags: `--output-format json|rich|plain` (default JSON), `-q/-v`, `--config`,
      `--templates-dir`, `--runtime local|container`, `--engine`, `--param`, `--dry-run`.
- [ ] `LocalProcessor`, `ContainerProcessor`, `DryRunProcessor` behind one processor port; factory
      composition; no backend switch statements.
- [ ] `show` re-extracts without writing files; `generate` writes `theme.json` + projections;
      `dump-templates` materializes the catalog.
- [ ] CLI tests cover every verb and the flags; JSON shapes are stable.
- [ ] `make gates` green.

## Done-when

`pytest tests/unit/cli tests/integration/test_cli -q` green; `tpr generate --dry-run` prints the
resolved command and projection list.

