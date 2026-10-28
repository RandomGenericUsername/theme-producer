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

Blocked by `SPIKE-001` and a released `tpr` tag. This is the only ticket allowed to edit the dotfiles
tree, and it lives in the dotfiles repo's own ticket system.

## Done-when

A dotfiles ticket proves the swap end-to-end on a real wallpaper with all consumers green.

