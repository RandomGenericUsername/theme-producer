# AGENTS.md — theme-producer operating contract

Canonical agent instructions for this repo. Claude (`CLAUDE.md` symlinks here), OpenCode, and all
BMAD/OpenSpec skills must follow this.

## 1. Evidence rule (hard requirement)

No suggestion "in the air". Every technical claim, recommendation, or design decision must carry
testable evidence — at least one of:

- **Doc evidence:** file path + line range, or commit SHA, or URL + quoted section.
- **Prototype evidence:** a script/command in-repo that runs and prints the validating output.
  State the exact command and observed result.
- **Test evidence:** `command run → result` (exit code + key output). Failing-as-expected counts if
  it validates the claim.

Format: any non-trivial claim gets an `Evidence:` line and a `Verify:` line (how to reproduce in one
command). If evidence doesn't exist yet, say `Evidence: MISSING — run <X> to produce it` and do not
present the claim as fact.

## 2. Charter — the theme producer

This repo owns one package, `theme-producer` (import package `theme_producer`, console script
`tpr`). It turns a wallpaper image (or a seed color / imported JSON) into a **Theme**: Material You
semantic roles, tonal palettes, and both light and dark modes. It then renders that Theme through a
bundled catalog of **projections** for the consumers in the dotfiles tree.

- **The Theme is the product.** A 16-color palette is a projection for ANSI-only consumers, never
  the domain model.
- **Semantic first.** Every projection that can carry named tokens does so; positional indices are
  compatibility aliases.
- **Engines are replaceable.** Color generation sits behind `ThemeEnginePort`.
  - v1 engine: `matugen` (pinned release, containerized, JSON only).
  - v2 engine: our own Rust helper on the MIT/Apache-2.0 `material-colors` crate.
  - A pure-Python engine is an explicit non-goal until a recorded revisit trigger fires.
- **CSG is untouched.** `color-scheme-generator` remains the production palette producer until the
  dotfiles wiring ticket proves this project can replace it. No edits to CSG from this repo.
- **Containerized by default.** One pinned image per engine, built by this repo's `install` verb
  through `oci-runtime`; the image tag is the pin, never `latest`.
- **Settings and catalogs** resolve through `config-assembler-engine` (single-file, no merging):
  `settings.toml` via the full pipeline, `engines.yaml` via the same pipeline, templates directory
  via `CompositePathResolver` only.
- **Output contract.** `theme.json` is canonical (versioned schema). Projections are pure functions
  of the Theme and must not read each other.

Sibling dependencies (`cli-output`, `config-assembler-engine`, `oci-runtime`, later
`cli-invocation-contract`) are consumed as immutable git tags, never paths and never `editable`.
The dotfiles runtime invocation contract is owned by the `contracts` repo, not this one.

## 3. How we work here

- Read files, run commands (`rg`, `git log`, `uv`, `pytest`, `podman`/`docker`,
  `openspec validate`), paste results. Prefer executed output over recalled text.
- When findings contradict an earlier claim, state the discrepancy and trust the evidence.
- Keep changes small, verifiable, committable. A suite that is green only on the author's host is
  not green: tests are hermetic (empty `HOME`/`XDG_*`, foreign cwd), enforced by
  `tests/conftest.py` plus a canary test.
- Never work on main: `scripts/worktree-guard.sh create <id> <slug>` scaffolds
  `ticket/<id>-<slug>` + `.worktrees/<id>/`, and aborts when the tree is dirty. Record
  worktree/branch in the ticket.
- A published tag is never moved or deleted; a fix is a new tag. PyPI is not a channel.

## 4. OpenSpec + BMAD routing (via tickets)

- All work starts as a ticket in `tickets/` (`_template/`, vocab + rollup in `INDEX.md`, flow in
  `LIFECYCLE.md`). Triage with `/triage` (lanes in `tickets/_fixtures/router-lanes.md`).
- Broad scope (product, requirements, architecture, cross-repo contract) → BMAD. Installed skills
  are exactly the five in `skills-lock.json`: `bmad`, `bmad-product-brief`, `bmad-spec`,
  `bmad-architecture`, `bmad-build`. Say so when a step needs a missing skill instead of
  improvising.
- Bounded slices (one proposal + spec + design + tasks) → OpenSpec (`/opsx-propose`,
  `/opsx-apply`, `/opsx-archive`). Artifact rules in `openspec/config.yaml` restate this evidence
  rule per artifact.
- Planning edits (tickets, `openspec/` changes, `_bmad-output/`, docs) and implementation changes
  (code, packaging, harness, CI) land in **separate commits** and never in the same turn.

## 5. Orchestration split

The planning/orchestration session writes tickets, BMAD/OpenSpec artifacts, lane assignments,
worktree setup, status transitions and closeouts. It does not write product code, tests, Dockerfiles
or templates. Those are build tickets executed in their ticket worktree by `bmad-build`, with their
own evidence and green gates; the orchestrator verifies and moves the ticket.

## 6. Gates

- `make gates` = `test lint hermetic lock-check docs-check`.
- `make build` produces sdist + wheel; `make image` builds the base + engine images at `v<version>`
  and runs `tpr version` inside the base image.
- CI runs one job per gate plus `ci-gates-parity`, which compares the workflow's job set against
  `GATES` in the `Makefile`, and an `image` job that builds and smoke-runs the containers.
- Verify: `make gates && make build && make image` → exit 0; `make ci-gates-parity` → exit 0.

## 7. License posture

This repo is MIT. The v1 engine (matugen) is GPL-2.0-or-later and is used **only** as a separate
process (argv in, JSON out); its code is never linked, imported, or copied. Any distributed image
that contains matugen carries its license text and the exact source reference. The v2 engine uses
the MIT/Apache-2.0 `material-colors` crate and carries its notices.
