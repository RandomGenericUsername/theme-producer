---
id: req-029
title: "Semantic btop component contract with contrast-safe gradients"
kind: requirement
status: in-progress
lane: 2
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-029/
branch: ticket/req-029-btop-semantic-gradients
---

# Semantic btop component contract with contrast-safe gradients

## Why

The generated `colors.btop.theme` paints the NET graphs in the same colour as the
empty meter (`download_end` == `meter_bg`), so the graphs are effectively
invisible. The btop projection currently records only `key -> MaterialRole`; it
does not record what each key means (data inbound, thermal pressure, used
capacity, chrome, ...), so it cannot choose a semantically correct, contrast-safe
graph family.

Evidence: `PROPOSAL.md` §1.1 and §3 in
`ags-btop-theme-studio/.worktrees/REQ-007/tickets/REQ-007-btop-gradient-ux/proposal/`
(approved Stage 0 artifact). Current mapping:
`src/theme_producer/adapters/projections/btop.py` maps `download_*` / `upload_*`
to `surface_container_low/mid/high`, the same roles used by `meter_bg` and the
free/available capacity families.

## Requirement

1. Add a semantic btop component contract: every one of the 48 documented keys
   belongs to a component, a semantic intent, and either a fixed Material role or
   a role family used for gradient resolution.
2. Gradient stops resolve from the existing six `Mode.palettes` tonal families,
   with dark/light anchor variants and a contrast guard. Tonal variants are
   internal contrast anchors, not a public authoring model.
3. Every visible graph/meter stop is at least 3:1 against its actual background
   (`meter_bg`, and `main_bg` for process text). If an anchor fails, shift within
   the same semantic family; never substitute an unrelated neutral surface.
4. Keep exactly the 48 documented btop keys. No new keys, no hardcoded hex, and
   no post-generation patch.
5. Preserve dark/light semantic equivalence with a mode-aware variant order.
6. Keep the Jinja template a pure iteration over projection rows.

## Acceptance

- [ ] Component contract covers exactly the 48 documented keys with no unknown
      keys and no unassigned intents.
- [ ] `download_end != meter_bg`; every download/upload stop is >= 3:1 against
      `meter_bg` for both modes.
- [ ] Every gradient component resolves through its assigned semantic family and
      the guard only shifts inside that family.
- [ ] Dark and light modes both pass the visibility and equivalence checks.
- [ ] Golden `colors.btop.theme` snapshot is regenerated and byte-identical.
- [ ] `make gates` passes (or every gate component is reported separately).
- [ ] Closeout (tag/release) — out of scope for this ticket; owner approval is a
      separate gate.

## Evidence

- Proposal: `ags-btop-theme-studio/.worktrees/REQ-007/tickets/REQ-007-btop-gradient-ux/proposal/PROPOSAL.md`
- Cycle: `ags-btop-theme-studio/.worktrees/REQ-007/tickets/REQ-007-btop-gradient-ux/proposal/DEV-CYCLE.md`
- Current projection: `src/theme_producer/adapters/projections/btop.py`
- Domain palettes: `src/theme_producer/domain/models.py`, `domain/enums.py`
- Template: `src/theme_producer/defaults/templates/colors.btop.theme.j2`
