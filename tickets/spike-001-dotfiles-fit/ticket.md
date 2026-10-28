---
id: SPIKE-001
title: "Dotfiles fit: adapter, hashes, contract, rollout"
kind: spike
status: reported
lane: 4 — bmad-advisory
timebox: "4h"
questions:
  - "What is the smallest runtime adapter change that can consume tpr's theme.json + eight projections?"
  - "How do the eight artifact hashes and the cache entry hash change (backend/settings are not in today's key)?"
  - "Which consumer pointers, reloaders and AGS palette-refresh paths need touching?"
  - "Is a contracts bump required, or can the eight filenames be kept stable?"
  - "What is the rollback path to CSG?"
answered:
  - "Q1: a sibling IColorSchemeGenerator adapter, not a generalized CsgAdapter; derive.ensure_palette must stop hardcoding csg_templates."
  - "Q2: today's ph = sha256(wallpaper_hash || csg_templates_hash); a producer/engine/settings fingerprint must enter the key and be recomputable by invalidation, or the switch is invisible."
  - "Q3: 5 consumer pointers + hypr/kitty/sequences direct readers + AGS appearance hash + ITR colors.yaml chaining; no new filenames needed."
  - "Q4: keep the 8 filenames; a new tpr invocation record is required, but meta.schema.json only changes if a fingerprint field or a 9th artifact is added."
  - "Q5: rollback is safe only with a producer fingerprint in the key; otherwise evict cache/palettes/<ph> + cascaded icons and re-set the wallpaper."
open:
  - "Where the producer fingerprint lives: seed-only vs a recorded meta field vs a composite inputs hash (contracts decision)."
  - "Whether theme.json ever becomes a 9th recorded artifact; it cannot ride in the entry today."
  - "Whether derive.ensure_palette becomes producer-agnostic or gets a parallel tpr path."
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: none
branch: none
---

# Dotfiles fit: adapter, hashes, contract, rollout

## Questions

- Smallest runtime adapter change that can consume `tpr`'s `theme.json` + eight projections?
- How do artifact hashes and the cache entry hash change, given
  `palette_entry_hash = sha256(wallpaper_hash || template_set_hash)` and no engine/settings in the
  key?
- Which consumer pointers, reloaders and AGS `palette-refresh` paths need touching?
- Is a contracts bump required, or can the eight filenames stay stable?
- What is the rollback path to CSG?

## Findings

### Dependency map

```
producer (csg, container, backend=pywal, tag v0.2.1)
  argv: csg generate <wallpaper> --format yaml|conf|gtk.css|adw.css|sequences|rasi|kitty|btop.theme
  env : COLORSCHEME__OUTPUT__DIRECTORY=<staging>/<ph>, COLORSCHEME__OUTPUT__OVERWRITE=true
        |
        v
cache/palettes/<ph>/  (8 files + meta.json; ph = sha256(wallpaper_hash || templates_hash))
        |
        v current/ symlinks -> consumer pointers -> reloaders / AGS refresh / ITR icons
```

Trigger correction: `wallpaper.state` is progress/UI only; `dotfiles-runtime wallpaper set` is the
producer trigger (`ags-apps/wallpaper-selector/lib/apply.ts:25`,
`dotfiles-runtime/src/runtime/cli/main.py:449-455`).

### Q1 — end-to-end path

- `wallpaper set` composition: `dotfiles-runtime/src/runtime/cli/main.py:617-641`
  (`find_templates_dir`, `CsgAdapter(templates_dir=...)`, `prepare_palette`).
- Pipeline: `application/apply_wallpaper.py:168-172` → `derive.ensure_palette`.
- Cache gate: `application/derive.py:692-697` (`template_set_hash = canonical_hash_dir(...)`,
  `peh = palette_entry_hash(...)`, `ensure_palette_entry_complete`).
- Producer call: `adapters/csg_adapter.py:467-494` (argv, env at `:459-464`).
- Artifact hash + meta: `csg_adapter.py:205-238`, `derive.py:710-726`,
  `seeder.py:307-336`.
- Atomic publish: `adapters/cache.py:517-613`; staging verification `:440-514`.
- Reconcile: `application/reconcile.py:273-289` (current links + consumer pointers), then
  reloaders at `:330-377`.

**Answer:** a new impl of the same port (`ports/color_scheme_generator.py:9-22`), because
`CsgAdapter` hardcodes `csg`, the eight `--format` tokens, `COLORSCHEME__*` env and a 330 s timeout
(`csg_adapter.py:68-74, 459-488`). But `derive.ensure_palette` also hardcodes
`require_input("csg_templates")` and hashes that dir (`derive.py:692-694`), so a sibling adapter alone
is not enough.

### Q2 — artifact/hash contract

- The 8 names: `dotfiles-runtime/src/runtime/domain/models.py:68-77`.
- Enforced in `csg_adapter.py:190-238, 582-597`, `derive.py:288-332, 715-724`,
  `seeder.py:485-494, 659-668`, `reconcile.py:556-565, 599-609, 662-672`, `doctor.py:35-44`,
  `inspect.py:341-351`, `json_state_repository.py:372-381`.
- Freeze: `contracts/schemas/meta.schema.json:29-73` (`additionalProperties:false` at both levels)
  and `contracts/invocation-contract.json:40-55` (`exact_filename`, `min_count: 8`). The runtime
  embeds a byte-identical schema copy and fails drift (`test_contract_schema_conformance.py:32-39`).
- Entry hash: `adapters/hashing.py:261-279` — `seed` is a spare input; no engine/backend/image/
  settings participate. `invalidation.py:146-159` only compares the templates hash.

**Answer:** keep the 8 filenames. A producer/engine/settings fingerprint must be folded into a value
that feeds both `palette_entry_hash` and `invalidation.recomputed()`; otherwise a producer switch
returns the old palette (`derive.py:696-697`). `theme.json` cannot be added to the palette entry
without a contract change: `verify_staging` rejects unrecorded files and
`match_entry_artifacts` requires every file to be recorded (`cache.py:296-328, 448-465`).

### Q3 — consumers

- Consumer pointers (5): `consumer_path_spec.py:48-57` — AGS + GTK3 → `colors.gtk.css`, GTK4 →
  `colors.adw.css`, rofi → `colors.rasi`, btop → `colors.btop.theme`.
- Direct readers: hypr `dotfiles-assets/configs/hypr/colors.lua:14-15` (`colors.conf`), kitty
  `dotfiles-assets/templates/kitty/kitty.conf.j2:2`, zsh `.../zsh/.zshrc.j2:33`
  (`colors.sequences`), btop `.../btop/btop.conf.j2:48`.
- Reloaders: `runtime/cli/main.py:389-421` (hypr, terminal, kitty, btop); GTK4 restart lane
  `gtk4_app_subscriber.py:129-132, 354-377`; AGS refresh `ags_app_refresh.py:592-599`,
  appearance hash `hashing.py:90-116`.
- Icons: `itr_adapter.py:346-417` passes `ICON_RENDERER__COLOR_SCHEME__PATH=<ph>/colors.yaml`;
  ITR preserves extra top-level keys (`file_color_scheme_loader.py:78-83`).

**Answer:** no new filenames needed. The semantic tokens ride inside `colors.gtk.css`,
`colors.adw.css`, `colors.yaml`, `colors.rasi`, `colors.conf`, `colors.btop.theme`; kitty and
sequences stay ANSI. `theme.json` is producer-side only unless the contract is versioned.

### Q4 — contracts

- CSG record: `contracts/invocation-contract.json:5-62` (argv/env/artifacts/timeout 60 s).
- Runtime pin: `dotfiles-runtime/pyproject.toml:45-47` and `src/runtime/adapters/CONTRACT_PIN`
  (`v0.2.0` / `5eb01b8`); provisioning verifies `contract 0.2.0`
  (`dotfiles-provision/ansible/roles/verify/vars/main.yml:371-380`).
- Provisioning gaps: `verify_palette_files` covers 6 of 8 (`verify/vars/main.yml:595-601`); the CSG
  template list covers 7 and omits `colors.btop.theme.j2` (`:247-254`).

**Answer:** add a `tpr` record (new contracts tag + re-pin) but keep `meta.schema.json` unchanged
if no fingerprint field/9th artifact is added. If a fingerprint is recorded in meta, both schema
copies and `test_contract_schema_conformance.py` change.

### Q5 — rollback

- With a producer fingerprint in the key: flip the selector back to `csg`, force a re-derive
  (`wallpaper set` or `regenerate`); existing CSG entries are reused if present.
- Without a key change: tpr bytes occupy the same `<ph>`; rollback requires evicting
  `cache/palettes/<ph>` and the cascaded icons entries, then re-setting the wallpaper. Reconcile is
  completeness-only and will not notice the switch (`reconcile.py:443-455`).

**Answer:** do not adopt without a key/invalidation change. Provisioning rollback is independent
(pin/image tag/settings template are untouched).

## Exact adoption surface (minimal path)

Runtime: `tpr_adapter.py` (new), `derive.py`, `hashing.py`, `invalidation.py`, `cli/main.py`,
`csg_adapter.py` (extract the 8-artifact verify/entry builder), `pyproject.toml`,
`CONTRACT_PIN`, plus the runtime tests listed below.

Contracts: `invocation-contract.json`, `CONTRACT.md`, `tests/test_record.py`,
`test_testkit_positive.py`, `test_testkit_negative.py`, `test_loader.py`; meta schema only if a
fingerprint/9th artifact is added.

Provisioning (only if tpr is pinned/containerized): `cli-tools.yaml`, `cli_tools/vars`,
`cli_tools/tasks`, `settings/vars`, new `tpr-settings.toml.j2`, `verify/vars`, `verify/tasks`,
`assets/vars`, `assets.yaml`.

Tests: `test_csg_adapter.py`, `test_csg_adapter_timeout_cleanup.py`,
`test_cli_invocation_contract.py`, `test_hashing.py`, `test_btop_theme_artifacts.py`,
`test_seed_cache.py`, `test_apply_wallpaper.py`, `test_wallpaper_visible_first.py`,
`test_reconcile.py`, `test_regenerate_stale.py`, `test_doctor_check.py`, `test_doctor_repair.py`,
`test_verify_cache.py`, `test_invalidation_query.py`, `test_cli_wallpaper_set.py`,
`test_cli_reconcile.py`; integration `test_csg_adapter_integration.py`,
`test_csg_determinism.py`, `test_required_palette*.py`,
`test_wallpaper_set_capstone_integration.py`.

## Risks / gotchas

1. Cache-key blindness is the highest risk (Q2). Switching producer without a key change silently
   reuses the old palette; reconcile is completeness-only.
2. `theme.json` cannot ride in the palette entry today (Q2). Keep it producer-side or version the
   contract.
3. Contracts freeze: 8 exact keys, `additionalProperties:false`; a 9th artifact cascades through
   runtime/contracts/provisioning/tests.
4. Consumer-pointer failures are skip+warn (`seeder.py:780-794`), so a rename silently leaves
   consumers stale.
5. AGS appearance hash includes the palette entry hash; no key change means the ledger gate can
   skip refresh; a key change cascades icons.
6. ITR only understands `colors.yaml`; a theme.json-only producer breaks icons.
7. The `current/` artifact list is duplicated in 4+ places; add/rename in one and the others drift.
8. Provisioning verify is incomplete (6/8 palette files, 7/8 templates); do not rely on it as the
   sole adoption gate.
9. Contract timeout (60 s) vs adapter (330 s) disagree; define tpr's timeout explicitly.
10. Contract pin is two-place (`pyproject.toml` tag + `CONTRACT_PIN`); both move on a bump.

## Recommendation

Adopt as a sibling adapter, keep the 8 filenames, add a producer fingerprint to the key and
invalidation, keep `theme.json` producer-side, add a `tpr` invocation record, and treat the
`derive.ensure_palette` csg-templates coupling as the first runtime change. No implementation in
this spike; the adoption ticket owns the code.
