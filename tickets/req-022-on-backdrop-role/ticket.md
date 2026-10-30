---
id: REQ-022
title: "Produced role: on_backdrop (ink over the wallpaper band)"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: none
worktree: none
branch: none
---

# Produced role: `on_backdrop`

## Requirement

Decision record (2026-10-30, user-approved): the v0.4.0 product freeze is
lifted for exactly one additive role. tpr remains the sole producer.
Consumers move to semantic roles and the runtime icon-contrast guard is
**deleted, not ported**. `on_backdrop` is the produced answer to "what ink reads
over this wallpaper's bar band?" — the question the guard was answering at the
wrong layer.

### Facts to build on

- `MaterialRole` is exactly the 50 engine-emitted Material roles:
  `src/theme_producer/domain/enums.py:17-76`.
- `Mode` enforces exactly those 50 roles:
  `src/theme_producer/domain/models.py:282-293`.
- Projection context exposes `roles` (all `MaterialRole`), `vocabulary` aliases,
  and `extra_roles`: `src/theme_producer/adapters/projections/registry.py:299-323`.
  `colors.yaml.j2` emits vocabulary + extra roles + the `colors` legacy list.
- The WCAG relative-luminance formula already exists in
  `src/theme_producer/adapters/image_metrics.py` (the `lin(c)` pipeline); smart
  mode's whole-image threshold is `smart_threshold` (default 0.5).
- The runtime guard's band definition to match:
  `dotfiles-runtime/src/runtime/adapters/icon_contrast_sampler.py:20-52`
  (top 48 rows, mean WCAG relative luminance, ≤64 px wide thumb).

### Design (normative)

1. **Produced, not engine.** Keep `MaterialRole` = the engine's 50. Add
   `Mode.on_backdrop: Color` (or a `produced` mapping if cleaner) with
   validation; round-trip it in `Mode.to_dict`/`from_dict`. theme.json schema
   gets an additive minor version bump.
2. **Measurement.** Top band of the source image = top `min(48, height)` rows,
   resized to ≤64 px wide; mean WCAG relative luminance, identical formula to
   the runtime sampler above. The constant is documented in
   `docs/VOCABULARY.md`.
3. **Selection.** Candidates are the mode's neutral-pole roles only, so the
   result is always a theme color and never a random hue:
   `on_surface, on_surface_variant, on_background, inverse_on_surface,
   inverse_surface, outline, outline_variant, surface, surface_dim,
   surface_container_lowest`.
   Pick the candidate with maximum WCAG contrast against the band luminance;
   ties prefer `on_surface`. Best-effort below 4.5 is documented (a theme color
   cannot beat a pathological band without inventing a color).
4. **Per mode, intentionally allowed to leave the ink family.** `on_backdrop`
   may sit on the opposite luminance pole from `on_surface` when the band
   disagrees with the scheme (dark scheme + bright band). That is its purpose;
   document it.
5. **No image source** (seed `color` or imported `json`): default
   `on_backdrop = on_surface`; document.
6. **Projections.** Emit in every named-token projection: `theme.json` (both
   modes), `colors.yaml`, `colors.gtk.css`, `colors.adw.css`, `colors.rasi`.
   ANSI/kitty/sequences/btop are unchanged (no slot).
7. **No consumer coupling.** tpr does not read icons.yaml or any consumer
   manifest; projections stay pure functions of the Theme.

## Acceptance

- [ ] theme.json carries `on_backdrop` in both modes; schema validates;
      additive version bump documented.
- [ ] Computation tests: bright band → dark candidate; dark band → light
      candidate; band/scheme disagreement covered; mid-gray → max-contrast
      best effort; seed/json → `on_surface`.
- [ ] All named-token projections carry the role; snapshot tests updated; ANSI
      outputs byte-identical.
- [ ] Deterministic and engine-independent: matugen vs native on the same
      image produce the same `on_backdrop`.
- [ ] `docs/VOCABULARY.md` lists the 50 engine roles + `on_backdrop` with the
      band constant and selection rule.
- [ ] `make gates` green; hermetic suite green.
- [ ] Release `v0.5.0` after orchestrator review.

## Evidence / Verify

- Evidence: `src/theme_producer/domain/enums.py:17-76`,
  `src/theme_producer/domain/models.py:282-293`,
  `src/theme_producer/adapters/projections/registry.py:299-323`,
  `dotfiles-runtime/src/runtime/adapters/icon_contrast_sampler.py:20-52`.
- Verify: `make gates` in this repo after implementation;
  `uv run tpr generate <image> --format json` then inspect
  `theme.json.modes.dark.on_backdrop`.
