---
id: EPIC-002
title: "Consumer semantic adoption of tpr roles"
kind: epic
status: in-progress
lane: 4 — bmad-advisory
links:
  openspec: none
  bmad: none
worktree: none
branch: main
done-when: "Every palette consumer that has chrome/semantic surfaces consumes tpr semantic roles (with legacy aliases only as fallback), and each consumer has visual + contract evidence."
---

# EPIC-002 — Consumer semantic adoption of tpr roles

## Why this exists

`REQ-014` covered the **runtime/provisioning cutover**: tpr generates the
palette, runtime caches it, producer selection is config-owned, and consumer
pointers are correct. That is done.

The user's definition of **adoption** is broader: consumers must actually wire
the new tpr roles, not merely receive legacy `colorN` aliases. This epic tracks
that consumer migration. `theme-producer v0.4.0` remains frozen; this is
consumer work, not producer work.

## Current consumer matrix

| Consumer | Current state | Adoption |
|---|---|---|
| AGS bar | legacy `@color_*` (103 uses) | open |
| AGS notifications | legacy `@color_*` | open |
| AGS capture | legacy `@color_*` | open |
| AGS clipboard | legacy `@color_*` | open |
| AGS ICME | legacy `@color_*`, 46 `@color_foreground`; live-refresh issue | **BUG-001** in `ags-icme` |
| AGS btop-theme-studio | legacy `@color_*`; 69 `@color_foreground`, 13 `@color_06` | **REQ-002** in `ags-btop-theme-studio` |
| AGS wallpaper-selector | legacy `@color_*` | open |
| Icons / ITR | variant `colorN` overrides | open; migrate where semantics are clear |
| rofi / GTK / wlogout / btop / kitty / Hyprland | consume emitted projections/aliases | verify, mostly file-level |

Source: `docs/CONSUMER-AUDIT-2026-10-28.md`; re-audit each consumer before
migration because the runtime cutover changed the live path.

## Definition of done

- Every consumer above has an explicit role mapping: semantic tpr role first,
  legacy alias only as fallback.
- No consumer silently depends on the legacy alias order for semantic meaning.
- ICME follows palette changes on a live wallpaper set and on launch/toggle.
- btop-theme-studio chrome uses semantic roles while the btop candidate preview
  remains a candidate-theme surface (not desktop chrome).
- Each consumer has tests/visual evidence for state, hover, focus and error
  colors, plus a no-regression check on the current wallpaper.
- No tpr product change is required for consumer adoption; if one is, it gets a
  separate theme-producer ticket.

## Rules

- **Do not close this epic by changing only aliases.** Aliases are compatibility;
  semantic adoption means the consumer chooses the right role.
- Do not change tpr role semantics to fit a consumer; map in the consumer.
- Keep the wallpaper-selector per-wallpaper scheme GUI as a separate feature.
- Keep the runtime cutover (`REQ-014`) closed; this epic is the remaining
  adoption phase.

## Child tickets

- `ags-icme` BUG-001 — ICME does not visibly follow palette changes / window
  toggle identity.
- `ags-btop-theme-studio` REQ-002 — semantic-role migration for the studio
  chrome.
- Remaining AGS apps and ITR: open as their audits complete, one ticket per
  consumer.

## Evidence

- Live palettes are distinct: default primary `#b9c3ff`; eagle primary
  `#ffb59a`; current `f39c2add…` palette. This rules out “all tpr palettes look
  the same” as the cause of the ICME report.
- `~/.config/ags/colors.css` defines `color_background`, `color_foreground`,
  `color_cursor` and `color_00..15`; the producer is emitting the compatibility
  layer.
- `appearance-ledger.json` marks `icon-color-mapping-editor` as `applied`, while
  its log reports `no window registered with name
  "icon-color-mapping-editor-window"`; the source names the window `icme-window`.
