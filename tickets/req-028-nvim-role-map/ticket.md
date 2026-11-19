---
id: req-028
title: "Neovim role map for skin @role resolution"
kind: requirement
status: in-progress
lane: 2
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-028/
branch: ticket/req-028-nvim-role-map
---

# Neovim role map for skin @role resolution

## Why

`dotfiles-v3` REQ-124 (`.worktrees/REQ-124/docs/116-neovim-skin-appearance.md`)
loads the bundled Neovim skins by resolving every `@role` reference from the
generated palette module. `colors.nvim.lua` currently exposes only the curated
subset in `M.palette`, so the loader cannot resolve roles outside that subset
(`surface_dim`, `inverse_primary`, `scrim`, `source_color`, ...). The full role
map must be exposed additively without changing `M.palette`.

Evidence: `src/theme_producer/defaults/templates/colors.nvim.lua.j2` before
this change emitted `M.palette` (28 curated roles + 16 ANSI slots) and no
full-role table. `ProjectionContext.roles` already carries all 50
`MaterialRole` values and `produced_roles` carries `on_backdrop`
(`src/theme_producer/adapters/projections/registry.py`,
`build_mode_context`).

## Requirement

1. `colors.nvim.lua.j2` emits `M.roles`, a Lua table mapping every Material
   palette role (all 50 `MaterialRole` values) plus the produced
   `on_backdrop` token to its selected-mode hex.
2. `M.palette` and `M.highlights` keep their existing shape and values.
3. Tests cover `M.roles` for dark and light modes, assert the map equals the
   complete role set, and syntax-check the rendered Lua when a `lua`
   interpreter is available.
4. The golden fixture (`tests/fixtures/projections/colors.nvim.lua`) is
   regenerated and remains byte-identical to the render.
5. No tags, release, version bump, pin, install, apply, or host mutation.

## Acceptance

- [x] `M.roles` contains every `MaterialRole` plus `on_backdrop`.
- [x] `M.palette` output is unchanged (golden diff only adds `M.roles`).
- [x] Dark and light `M.roles` tests pass.
- [x] Rendered Lua loads via `lua -e 'assert(loadfile(...))'`.
- [x] `make test` and `make lint` pass.
- [ ] Closeout (tag/release) — out of scope for this ticket.

Evidence: `make test` / `make lint` results recorded in the handoff; see
`tests/unit/adapters/projections/test_template_content.py`.
Verify: `TEMPLATES_DIR=$PWD/src/theme_producer/defaults/templates make test`
