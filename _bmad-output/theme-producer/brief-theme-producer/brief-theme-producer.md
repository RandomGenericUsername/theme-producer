---
title: "Theme Producer — product brief"
status: draft
created: 2026-10-27
updated: 2026-10-27
---

# Theme Producer — product brief

## Problem

The dotfiles tree gets all of its colors from `color-scheme-generator` (CSG). CSG's model is a
16-color palette plus background/foreground/cursor, sorted by luminance. That model is a ramp, not
a semantics system, and every consumer pays for it:

- GTK/Adwaita, the AGS bar, icons, rofi, wlogout and hyprland want named roles (`surface`,
  `on_surface`, `primary`, `outline`, `error`, …), not `color4`.
- The icon vocabulary already expects `surface`, `accent` and `accent-muted`
  (`dotfiles-assets/icons/mappings/defaults.yaml:16-18`), but `colors.yaml` never emits them, so
  those mappings are dangling.
- Terminals genuinely need 16 ANSI colors, but CSG's 16 are luminance-sorted, so `color1` is not
  red and `color4` is not blue.

The result is a theme that cannot express Material You's role set, and a terminal palette whose
indices have no semantic meaning.

## Solution

A new theme producer (`tpr`), a sibling of CSG:

1. **Theme is the root object.** `Theme` = source metadata + scheme + contrast + two modes
   (`dark`, `light`), each with the 50 Material roles and the six tonal palettes (18 tones each).
2. **Projections, not a single palette.** Each consumer gets a projection of the Theme:
   - open/semantic: GTK3, GTK4/Adwaita, AGS (via GTK CSS), icons (`colors.yaml`), rofi, wlogout,
     hyprland, btop;
   - fixed: kitty and `colors.sequences` get a deliberate 16-color ANSI projection.
3. **Canonical `theme.json`** (versioned schema) is the only source of truth. Projections are pure
   functions of it and never read each other.
4. **Engines are replaceable** behind `ThemeEnginePort`: v1 matugen (pinned, containerized, JSON
   only), v2 our own Rust helper on the MIT/Apache `material-colors` crate. A pure-Python engine is
   a recorded non-goal.
5. **Drop-in shape.** Projections keep the eight filenames the dotfiles runtime already consumes,
   plus `theme.json`, so the eventual runtime adapter is mechanical.

## Who it serves

The dotfiles tree first (runtime, provisioning, icons, AGS, GTK, rofi, btop, kitty, wlogout,
hyprland), and through it the user. The CLI is also usable standalone: `tpr generate wall.png`
produces a complete theme directory.

## What is different

- Semantic first; positional indices are compatibility aliases.
- One run emits both dark and light themes.
- A real ANSI intent palette (hue-anchored), not a luminance ramp.
- `theme.json` gives every consumer the full role set; terminal-only consumers still get 16.
- The engine is a port, so the GPL binary can be replaced by our own MIT/Apache engine without
  touching the domain or projections.

## Success criteria

- `tpr generate <wallpaper>` writes `theme.json` plus the eight projection files; every file is
  generated from the same Theme.
- Every semantic token referenced by the projections exists in `theme.json`; golden tests enforce
  the capability tables.
- The ANSI projection passes hue/contrast assertions for the standard six hues.
- `make gates` green on a fresh clone; `make image` builds and smoke-runs the images; CI parity
  green.
- The later dotfiles adoption ticket can swap CSG for `tpr` without changing the runtime's artifact
  contract (or with a declared, versioned contract change).

## Scope

In: Theme model, settings, engine port + matugen/native engines, projections, ANSI recipe, CLI,
container images, tests, docs.

Out: changes to CSG, changes to the dotfiles tree, a pure-Python color engine, matugen's template
engine/wallpaper/hooks/config format, GUI, runtime light/dark switching, PyPI publishing.

## Vision

One theme, expressed correctly to every consumer: full Material semantics where the format allows
it, a deliberate ANSI palette where it does not. CSG remains the historical producer; `tpr` becomes
the one the dotfiles eventually adopt.
