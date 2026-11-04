---
id: EPIC-003
title: "Post-migration feedback: triage and patch batches"
kind: epic
status: done
lane: 3
links:
  openspec: none
  bmad: none
worktree: none
branch: main
done-when: "Every reported post-migration item is classified, fixed in its owning repo, verified live, and the batch pin is deployed."
---

# EPIC-003 — Post-migration feedback

Tracker for feedback after the palette.v1 consumer migration (EPIC-002). Rule:
one ticket per root cause in the owning repo; deploy in batches, never one
bootstrap per item.

## Intake / triage table

| # | Report | Classification | Owning repo | Ticket | Batch |
|---|---|---|---|---|---|
| F1 | Bar workspace/palette does not update after wallpaper change; notification: “Could not update: bar (ags, unknown) … outside the deployed link” | Migration regression (runtime discovery skips bare `ags run`) | dotfiles-runtime | BUG-008 | **done** (PIN-0129) |
| F2 | Rofi fails: `Parser error … File: ~/.config/rofi/colors.rasi` | Producer bug (rasi projection uses GTK `@define-color`) | theme-producer | BUG-004 | **done** (PIN-0129) |
| F4 | Rofi always looks the same after wallpaper changes | Static-config mapping bug: rofi used `@color01` = Material **error**, invariant in every palette | dotfiles-assets | assets v0.6.4 | **done** (PIN-0130) |
| F3 | Notification card text overlaps (window text bleeding through) | Card translucency (`alpha(@surface, 0.92)`) | ags-notifications | BUG-001 | **done** (PIN-0131) |

## Batch plan

- **PIN-0129**: tpr v0.5.1 (rasi) + runtime v0.5.2 (bar discovery). One
  bootstrap; verify bar refresh + rofi launch.
- Any further items join the next batch after classification; design-level
  items get a before/after preview before coding.

## Rules

- No per-item bootstrap; no silent reclassification (an item is either a bug,
  a design decision, pre-existing, or backlog).
- Each fix records evidence (test + live check) on its ticket.

## Outcome — batch closed 2026-11-04

All four reported items are fixed, deployed and verified live:

| Item | Fix | Deploy |
|---|---|---|
| F1 bar not refreshing | runtime v0.5.2: bare `ags run` attributed; applied/restart | PIN-0129 |
| F2 rofi parse error | tpr v0.5.1: valid rasi block | PIN-0129 |
| F3 toast bleed-through | notifications v0.2.1: opaque card | PIN-0131 |
| F4 rofi invariant colors | assets v0.6.4: role-based config; engine v0.1.32 | PIN-0130 |

Live at close: tpr 0.5.1, runtime 0.5.2, assets 0.6.4, engine 0.1.32,
notifications 0.2.1; doctor clean; rofi parses. EPIC closed; the next feedback
batch gets a new epic.
