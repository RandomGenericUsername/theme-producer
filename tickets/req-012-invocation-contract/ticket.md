---
id: REQ-012
title: "contracts record + conformance test (blocked)"
kind: requirement
status: done
lane: 3 — ticket-multi
parent: EPIC-001
links:
  openspec: req-012-invocation-contract
  bmad: none
worktree: none
branch: none
---

# contracts record + conformance test (blocked)

## Requirement

Declare `tpr` in the `contracts` repo (`cli-invocation-contract`) and add the conformance test that
runs the installed CLI against the record.

## Acceptance

- [ ] A `contracts` repo ticket adds the `tpr` record (argv, env, artifacts, timeout, exit codes).
- [ ] This repo depends on the released `cli-invocation-contract` tag (never a path).
- [ ] `tests/contract/test_invocation_contract.py` uses the conformance kit; no duplicated argv/
      artifact literals.
- [ ] `make gates` green against the released contract.

## Blocker

Blocked on a cross-repo release. The artifact set is stable as of `v0.1.0` (8 consumer files +
theme.json). Next: a `contracts` repo ticket adds the `tpr` record, a contracts tag is released, then
this repo pins it and adds `tests/contract/test_invocation_contract.py`. Do not invent a local
contract record.

## Done-when

Contract test green against a released `cli-invocation-contract` tag.

