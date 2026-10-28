---
id: REQ-014
title: "Dotfiles runtime/provisioning adoption (after spike)"
kind: requirement
status: proposed
lane: 4 — bmad-advisory
parent: EPIC-001
links:
  openspec: req-014-dotfiles-adoption
  bmad: none
worktree: none
branch: none
---

# Dotfiles runtime/provisioning adoption (after spike)

## Requirement

Adopt `tpr` in the dotfiles tree after the spike reports, without breaking the runtime artifact
contract.

## Acceptance

- [ ] A runtime adapter invokes `tpr` (or a generalized producer adapter) and populates the palette
      cache; artifact hashes and generation identity are mapped.
- [ ] Provisioning pins the released `tpr` tag and builds the images; the verify role names them.
- [ ] Consumer pointers, reloaders and the AGS palette-refresh path are exercised.
- [ ] CSG remains available for rollback for one cycle; its removal is a separate ticket.
- [ ] No unversioned contract change.

## Blocker

Blocked on a cross-repo change. `SPIKE-001` is reported and `v0.1.0` is tagged. Next: a ticket in the
dotfiles repo (its own harness) implements the sibling adapter, the producer fingerprint in the
palette hash/invalidation, the producer selector, provisioning pin/build/verify, and the contracts
pin. This repo stays untouched during adoption.

## Done-when

A dotfiles ticket proves the swap end-to-end on a real wallpaper with all consumers green.

