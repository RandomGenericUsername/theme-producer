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

- [x] Component contract covers exactly the 48 documented keys with no unknown
      keys and no unassigned intents.
- [x] `download_end != meter_bg`; every download/upload stop is >= 3:1 against
      `meter_bg` for both modes.
- [x] Every gradient component resolves through its assigned semantic family and
      the guard only shifts inside that family.
- [x] Dark and light modes both pass the visibility and equivalence checks.
- [x] Golden `colors.btop.theme` snapshot is regenerated and byte-identical.
- [x] `make gates` passes (or every gate component is reported separately).
- [ ] Closeout (tag/release) — out of scope for this ticket; owner approval is a
      separate gate.

## Implementation evidence

- `make gates` → exit 0: `test` 669 passed / 88 skipped, `lint` clean,
  `hermetic` 666 passed / 37 skipped, `lock-check` clean, `docs-check` clean.
- `make build` → exit 0: sdist + wheel `0.7.1`.
- `make ci-gates-parity` → exit 0.
- `make image IMAGE_ENGINE=podman` → exit 0: base, matugen 4.2.0 and native
  `0.1.0` images at `v0.7.1`.
- The contrast guard fails closed when no variant in the assigned family can
  reach 3:1; it never substitutes another family or emits an invisible stop.
- Fixture sample (`tests/fixtures/theme.json`, 48 keys):
  - dark `meter_bg=#806a57`;
    `download_start/mid/end = #f2c7a1/#f9cda6/#ffd2aa` at
    `3.269/3.476/3.656:1`;
    `upload_start/mid/end = #f2c8a2/#facea8/#ffd3ab` at
    `3.293/3.512/3.682:1`.
  - light `meter_bg=#9a8068`;
    `download_start/mid/end = #40352b/#332a22/#191511` at
    `3.213/3.787/4.895:1`;
    `upload_start/mid/end = #40362c/#342b24/#1a1613` at
    `3.177/3.732/4.847:1`.
- Verify: `make gates && make build && make ci-gates-parity`; contrast table:
  `uv run pytest -q tests/unit/adapters/projections/test_btop.py`.

## Evidence

- Proposal: `ags-btop-theme-studio/.worktrees/REQ-007/tickets/REQ-007-btop-gradient-ux/proposal/PROPOSAL.md`
- Cycle: `ags-btop-theme-studio/.worktrees/REQ-007/tickets/REQ-007-btop-gradient-ux/proposal/DEV-CYCLE.md`
- Current projection: `src/theme_producer/adapters/projections/btop.py`
- Domain palettes: `src/theme_producer/domain/models.py`, `domain/enums.py`
- Template: `src/theme_producer/defaults/templates/colors.btop.theme.j2`
