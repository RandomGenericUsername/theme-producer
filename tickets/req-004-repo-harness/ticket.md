---
id: REQ-004
title: "Executable harness: packaging, gates, CI, hermetic tests"
kind: requirement
status: in-progress
lane: 2 — openspec-single
parent: EPIC-001
links:
  openspec: req-004-repo-harness
  bmad: none
worktree: .worktrees/req-004/
branch: ticket/req-004-repo-harness
---

# Executable harness: packaging, gates, CI, hermetic tests

## Requirement

Turn the planning substrate into an executable Python project with the CSG-proven harness, so every
later ticket lands on a green, hermetic baseline.

## Acceptance

- [ ] `pyproject.toml` (hatchling, src layout, console script `tpr`, Python 3.14) with deps
      `cli-output`, `config-assembler-engine`, `oci-runtime` pinned as git tags, plus `jinja2`,
      `pydantic`, `rich`, `typer`; dev group `pytest`, `pytest-cov`, `ruff`.
- [ ] `uv lock` and `uv sync --frozen` succeed; `uv.lock` committed.
- [ ] `Makefile` targets: `sync test lint format hermetic lock-check docs-check gates build
      ci-gates-parity`; `image` is added by REQ-011 and declared CI-only until then.
- [ ] `.github/workflows/gates.yml` has one job per gate plus `ci-gates-parity`; the parity script
      is adapted from CSG and exits non-zero when the sets differ.
- [ ] `tests/conftest.py` pins a hermetic HOME/XDG/foreign cwd; `tests/test_hermetic_canary.py`
      proves it runs.
- [ ] `src/theme_producer/__init__.py` carries `__version__`; a minimal `cli/main.py` exposes
      `tpr version` only (the rest arrives in REQ-010).
- [ ] `docs-check` asserts README/CHANGELOG/LICENSE/AGENTS and the `CLAUDE.md` symlink.
- [ ] `make gates`, `make build`, `make ci-gates-parity` exit 0 on a fresh clone.

## Done-when

`make gates && make build && make ci-gates-parity` exit 0 with empty HOME/XDG and a foreign cwd.

