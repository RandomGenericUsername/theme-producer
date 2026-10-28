---
id: SPIKE-001
title: "Dotfiles fit: adapter, hashes, contract, rollout"
kind: spike
status: boxed
lane: 4 — bmad-advisory
timebox: "4h"
questions:
  - "What is the smallest runtime adapter change that can consume tpr's theme.json + eight projections?"
  - "How do the eight artifact hashes and the cache entry hash change (backend/settings are not in today's key)?"
  - "Which consumer pointers, reloaders and AGS palette-refresh paths need touching?"
  - "Is a contracts bump required, or can the eight filenames be kept stable?"
  - "What is the rollback path to CSG?"
answered: []
open: []
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: none
branch: none
---

# Dotfiles fit: adapter, hashes, contract, rollout

## Questions

- What is the smallest runtime adapter change that can consume `tpr`'s `theme.json` + eight
  projections?
- How do the eight artifact hashes and the cache entry hash change, given
  `palette_entry_hash = sha256(wallpaper_hash || template_set_hash)` (`hashing.py:261-279`) and no
  engine/settings in the key?
- Which consumer pointers, reloaders and AGS `palette-refresh` paths need touching?
- Is a contracts bump required (`contracts/schemas/meta.schema.json:29-70` freezes eight artifact
  keys), or can the eight filenames stay stable?
- What is the rollback path to CSG?

## Findings

### Answered

- <pending>

### Open

- <pending>

> Spike stops at the box and reports `answered:` / `open:`. Implementation output from a spike is a
> failure.
