---
id: REQ-022
title: "Produced role: on_backdrop (ink over the wallpaper band)"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: none
worktree: .worktrees/req-022/
branch: ticket/req-022-on-backdrop-role
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

## Progress / evidence (build)

Implementation commit: `476fc0b` on `ticket/req-022-on-backdrop-role`
(worktree `.worktrees/req-022/`). Status intentionally left `in-progress` for
orchestrator review and release.

### What landed

- `on_backdrop` is a produced role on each `Mode` (default and no-image
  fallback `on_surface`), not a 51st `MaterialRole`; `MaterialRole` remains the
  engine's exactly 50. `theme.json` schema is now `1.1` (additive mode property
  `on_backdrop`). Legacy schema `"1"` and a missing `on_backdrop` are accepted
  on import and upgraded, so an old saved theme still loads.
- Band measurement lives in
  `adapters/image_metrics.py:measure_top_band_luminance`: top
  `min(48, height)` rows, resized to ≤64 px wide/high, mean WCAG relative
  luminance. The sRGB/Rec.709 formulas moved to the shared pure module
  `domain/color_metrics.py` and are reused by the existing metrics adapter.
- Selection is pure in `domain/on_backdrop.py`: the ten neutral-pole
  candidates, max WCAG contrast, ties to `on_surface` (candidate order),
  best-effort below 4.5. `adapters/on_backdrop.py` applies it after the engine
  output inside `LocalProcessor`, so matugen and native agree for one image.
- Named-token projections emit it: `theme.json` both modes, `colors.yaml`,
  `colors.gtk.css`, `colors.adw.css`, `colors.rasi`, `colors.conf`. ANSI,
  kitty, sequences, and btop templates/goldens are untouched.
- `docs/VOCABULARY.md` documents the 50 engine roles, `on_backdrop`, the 48-row
  band, the ≤64 px thumb, the candidate/selection rule, tie/fallback behavior,
  and the intentional opposite-pole case. `CHANGELOG.md`, `README.md`, and
  `native/README.md` carry the schema `1.1` note.

### Commands and results

- `uv sync --frozen` → exit 0 (CPython 3.14.7, 33 packages).
- `uv run pytest -q -rs` → **628 passed, 88 skipped** (engine/container/
  wallpaper-dependent tests skip honestly: matugen, tpr-native, image smoke).
- `make gates` → **exit 0**: `test` (628 passed, 88 skipped), `lint`
  (ruff: all checks passed), `hermetic` (624 passed, 37 skipped), `lock-check`
  (`uv lock --check`, resolved 34 packages), `docs-check` (silent pass).
- `make ci-gates-parity` → **PASS** gates `[docs-check, hermetic, lint,
  lock-check, test]`, jobs include `image` as declared CI-only.
- Golden refresh: re-rendered only `yaml`, `gtk`, `adw`, `rasi`, `conf` from
  `tests/fixtures/theme.json`; `git status` showed no changes to
  `colors.btop.theme`, `colors.kitty`, `colors.sequences`, or `theme.html`
  (byte-identical).
- `git diff --check` → clean (before the implementation commit).

### New/changed tests

- `tests/unit/domain/test_on_backdrop.py` — candidate set, bright band → dark,
  dark band → light, scheme/band disagreement across the ink pole, mid-gray
  best effort below 4.5, tie → `on_surface`, per-mode apply, engine
  independence.
- `tests/unit/adapters/test_on_backdrop.py` — image measurement applied to both
  modes, seed-color/json fallback, missing/undecodable fallback, same-image
  engine independence, canonical JSON round trip.
- `tests/unit/adapters/test_image_metrics.py` — 48-row crop, short-image whole
  band, ≤64 px resize, determinism, decode error.
- `tests/unit/domain/test_models.py`, `tests/unit/adapters/test_theme_json.py`,
  projection registry/template/golden tests, and engine/integration schema
  assertions updated for schema `1.1` and the produced mode property.

### Risk / notes

- Schema string is `"1.1"` (additive minor). The native Rust helper's constant
  was bumped to `1.1`; the Python native adapter also stamps `1.1` on older
  helper payloads so a pre-built `tpr-native` still parses.
- Package version is still `0.4.0`; `v0.5.0` release/tagging remains
  orchestrator-owned per the ticket.

Verify: `make gates` in `.worktrees/req-022/`, then
`uv run tpr generate <image> --format json` and inspect
`theme.json.modes.dark.on_backdrop` / `theme.json.modes.light.on_backdrop`.

## Evidence / Verify

- Evidence: `src/theme_producer/domain/enums.py:17-76`,
  `src/theme_producer/domain/models.py:282-293`,
  `src/theme_producer/adapters/projections/registry.py:299-323`,
  `dotfiles-runtime/src/runtime/adapters/icon_contrast_sampler.py:20-52`.
- Verify: `make gates` in this repo after implementation;
  `uv run tpr generate <image> --format json` then inspect
  `theme.json.modes.dark.on_backdrop`.
