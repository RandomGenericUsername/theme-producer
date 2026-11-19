---
id: req-027
title: "Neovim palette projection (colors.nvim.lua)"
kind: requirement
status: in-progress
lane: 2
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-027/
branch: ticket/req-027-nvim-projection
---

# Neovim palette projection (colors.nvim.lua)

## Why

Neovim is the last major consumer on a fixed colorscheme. The palette producer
already renders every other desktop surface from the wallpaper. `REQ-123` in
`dotfiles-v3` makes Neovim a first-class palette consumer; this ticket owns the
producer-side projection.

## Requirement

1. Add `colors.nvim.lua.j2` emitting a self-contained Lua module:
   - `M.name`, `M.mode`, `M.palette` (semantic roles plus 16 ANSI slots),
   - `M.highlights` (core editor, diagnostics, diff, LSP),
   - `M.links` (Treesitter/LSP aliases),
   - `M.load()` applying the highlights and terminal colors.
2. Register `nvim` as an open projection (`colors.nvim.lua`), add the
   consumer-facing format `nvim.lua`, and include it in the runtime default
   projection set.
3. Add a content test for both dark and light modes, and update the existing
   projection/file-list pins.
4. No tags/releases in this phase.

## Acceptance

- [ ] `colors.nvim.lua` renders for dark and light.
- [ ] The module contains `M.load`, `M.highlights`, `M.palette.ansi`, and the
      expected role hex values.
- [ ] `make test` passes.
- [ ] No tag/release.
