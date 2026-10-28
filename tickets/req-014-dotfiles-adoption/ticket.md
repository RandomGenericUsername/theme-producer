---
id: REQ-014
title: "Dotfiles runtime/provisioning adoption (after spike)"
kind: requirement
status: proposed
lane: 4 — bmad-advisory
parent: EPIC-001
links:
  openspec: req-014-dotfiles-adoption
  bmad: none
worktree: none
branch: none
---

# Dotfiles runtime/provisioning adoption (after spike)

## Requirement

Adopt `tpr` in the dotfiles tree after the spike reports, without breaking the runtime artifact
contract.

## Acceptance

- [ ] A runtime adapter invokes `tpr` (or a generalized producer adapter) and populates the palette
      cache; artifact hashes and generation identity are mapped.
- [ ] Provisioning pins the released `tpr` tag and builds the images; the verify role names them.
- [ ] Consumer pointers, reloaders and the AGS palette-refresh path are exercised.
- [ ] CSG remains available for rollback for one cycle; its removal is a separate ticket.
- [ ] No unversioned contract change.

## Current state (2026-10-28)

The cross-repo slices are done and released:

- `contracts v0.4.0` — the `tpr` record + tests, pushed.
- `dotfiles-runtime v0.4.0` — `TprAdapter`, `THEME__` allowlist, producer fingerprint in the cache
  key, `RUNTIME__PALETTE__PRODUCER` selector defaulting to `csg`; pushed.
- `dotfiles-provision v0.1.22` — tpr pin, three images, settings, templates, verify and the runtime
  producer switch; pushed.
- `theme-producer v0.1.0` — `cli-invocation-contract v0.4.0` pinned; conformance test green with
  `tpr-native`.

## Container validation (2026-10-28)

`docs/CONTAINER-VALIDATION-2026-10-28.md` records the real-wallpaper run:

- Host matugen absent; both `tpr-matugen-podman:v0.1.0` and `tpr-native-podman:v0.1.0` ran via
  `--runtime container --container-engine podman`.
- Seven wallpapers (six real files + the currently applied one), both engines: all exit 0, 9 files,
  50 roles, 6×18 palettes, 16 distinct ANSI colors, hue anchors exact, schema-valid `theme.json`.
- 8K wallpaper ~15 s including container startup; no host matugen cache/config created.
- Finding: same-seed parity is exact, but image-source selection can diverge (zenitsu: matugen
  `#f9c711` vs native `#f13802`). For the first cutover keep `engine = "matugen"`; native needs its
  source-color preference aligned before it can be a visual drop-in.

## Blocker

The `dotfiles-v3` composition pin is blocked by the in-flight `REQ-008` all-standalone cutover.
The composition is still engine `v0.1.19` with all seven AGS apps `owner: legacy`
(`dotfiles/provisioning/apps.yaml:30-38`), while engine `v0.1.21+` requires every entry to be
`owner: standalone`. Pinning engine `v0.1.22` now would combine the all-standalone topology change
with the tpr pin and fail the composition gates.

Next: after the REQ-008 v0.1.21 cutover lands in `dotfiles-v3`, make one combined pin release:

- engine `v0.1.22`
- runtime `v0.4.0`
- theme-producer `v0.1.0`
- assets `v0.6.2` (from the REQ-008 cutover)

with `apps.yaml` flipped to standalone, `deploy-coverage` green, and `runtime_palette_producer`
kept at `csg` until the user flips it.

## Done-when

A dotfiles ticket proves the swap end-to-end on a real wallpaper with all consumers green.

