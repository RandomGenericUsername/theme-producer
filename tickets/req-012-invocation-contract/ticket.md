---
id: REQ-012
title: "contracts record + conformance test (blocked)"
kind: requirement
status: proposed
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

Blocked until the artifact set is stable (after REQ-008/009) and a `contracts` release exists. Do not
invent a local contract record.

## Done-when

Contract test green against a released `cli-invocation-contract` tag.

