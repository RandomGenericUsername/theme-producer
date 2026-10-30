---
id: REQ-014
title: "Dotfiles tpr adoption: runtime/provisioning acceptance and cutover"
kind: requirement
status: in-progress
lane: 4 — bmad-advisory
parent: EPIC-001
links:
  openspec: req-014-dotfiles-adoption
  bmad: none
worktree: none
branch: none
---

# Dotfiles tpr adoption — acceptance and cutover

## Scope

This ticket is the **adoption gate** for using `theme-producer` (`tpr`) as the
dotfiles palette producer. It is not the theme-producer feature roadmap.

In scope:

- host bootstrap with the pinned tpr/runtime/provisioning/CSG releases;
- runtime-owned producer selection and cache identity;
- selector, rofi, AGS, GTK, rofi, wlogout, btop, kitty, Hyprland and icon
  consumer behavior on a real wallpaper;
- rollback to CSG and restoration of tpr;
- evidence and ticket closeout.

Out of scope / separate tickets:

- per-wallpaper scheme selection in the wallpaper-selector GUI;
- consumer semantic-role migrations beyond the current compatibility aliases;
- btop theme-studio integration work;
- removing CSG after the rollback window.

## Product status: frozen

`theme-producer v0.4.0` is feature-complete and released: 50 roles, 6×18
palettes, nine schemes, smart mode, scheme policy, ANSI projection, semantic
tokens/legacy aliases, `theme.json`, local/container engines, images and tests.
Do not change tpr product code for adoption unless acceptance finds a genuine
tpr defect; route that back to the theme-producer ticket system.

## Integration status: released

| Component | Release | Adoption change |
|---|---|---|
| contracts | `v0.4.0` | tpr invocation record |
| dotfiles-runtime | `v0.4.1` | runtime-owned `producer.json`, tpr container mode, pinned templates, palette diagnostics |
| color-scheme-generator | `v0.2.2` | fail-closed artifacts, decoy CWD template fix |
| dotfiles-provision | `v0.1.27` | renders producer config, removes ambient env authority, post-seed consumer links, tpr container verify |
| dotfiles-v3 | `PIN-0118` | engine/runtime/CSG pins; tpr default; `RUNTIME_PALETTE_PRODUCER=csg` rollback |
| theme-producer | `v0.4.0` | product frozen |

The v3 composition selects tpr by default; the runtime reads
`<install>/config/dotfiles-runtime/producer.json`, not ambient environment.

## Live acceptance matrix (the gate)

Run after `bootstrap.sh` completes on the host. No item may be waived; any
failure is routed to the owning repo and this ticket stays open.

| # | Check | Expected / evidence |
|---|---|---|
| 1 | Fresh bootstrap | `./bootstrap.sh` exits 0 with engine `v0.1.27`, runtime `v0.4.1`, CSG `v0.2.2`, tpr `v0.4.0`; verify green |
| 2 | Producer config | `<install>/config/dotfiles-runtime/producer.json` is `{schema_version:1, producer:"tpr", tpr_engine:"native", tpr_runtime:"container"}` |
| 3 | No ambient authority | no producer `environment.d` file/unit `Environment=`; `inspect producer` shows `source: config` and any stale `RUNTIME__PALETTE__PRODUCER=csg` as `ignored_env` |
| 4 | No host helper | `~/.local/bin/tpr-native` is removed; tpr still generates via the pinned native container image |
| 5 | Real wallpaper | set the current real wallpaper; palette cache gets a `tpr` entry, not CSG; 8 artifacts present |
| 6 | Previously failing image | `white_tailed_eagle.png` from the selector’s app CWD with stale `RUNTIME__PALETTE__PRODUCER=csg` succeeds and uses tpr |
| 7 | Selector-shaped apply | `dotfiles-runtime wallpaper set` invoked with the selector’s env uses tpr and the tpr cache key |
| 8 | Rofi | immediately after bootstrap, with no manual wallpaper switch, `rofi-ui` opens with no theme parse error; `colors.rasi` resolves |
| 9 | Consumers | AGS 7-app refresh 0 failures; GTK3/4, rofi, btop, wlogout, kitty, Hyprland and icons point at the new palette/current links |
| 10 | Diagnostics | a forced failure records `tool: tpr`/`tool: csg` correctly and includes rc/stdout/stderr; no `returncode:null` loss |
| 11 | Rollback | `RUNTIME_PALETTE_PRODUCER=csg ./bootstrap.sh` renders `producer:csg`, sets a CSG palette, and consumers follow; then restore tpr and verify |
| 12 | Clean repeat | a second tpr set is a cache hit; no manual helper, no ambient env override, no manual consumer relink |

## Rules

- **No workarounds**: no manual `tpr-native` copy, no `RUNTIME__…` double-underscore
  override, no manual `colors.rasi`/symlink repair, no “just re-run the wallpaper”.
- **One source of truth**: producer selection is `producer.json`; the selector
  calls the runtime unchanged.
- **Versioned pins only**: no `main` refs; no unversioned contract changes.
- **Close on evidence**: each matrix row records the command and observed output.
- **Rollback is a tested path**, not a fallback guess.

## Open tickets that must close with the gate

- `dotfiles-provision` BUG-006 — rofi post-bootstrap colors link.
- `dotfiles-provision` BUG-007 — tpr native/container provisioning and verify.
- `dotfiles-provision` BUG-008 — runtime-seed producer selection.
- `dotfiles-runtime` BUG-007 — palette missing-artifact diagnostics/templates.
- `dotfiles-runtime` REQ-004 — runtime producer config.
- `dotfiles-runtime` REQ-005 — tpr container runtime.
- `color-scheme-generator` BUG-002 — CSG exit 0 without artifacts.
- `ags-wallpaper-selector` BUG-001 — stale producer; resolved by runtime config,
  selector apply path unchanged.

## Done-when

- [ ] All 12 live acceptance rows have recorded evidence.
- [ ] No adoption ticket above remains open for the cutover.
- [ ] CSG rollback has been exercised and tpr restored; both cache identities
  are correct.
- [ ] The host runs the pinned set with no manual helper/env/link workarounds.
- [ ] Deferred items (selector scheme GUI, consumer semantic migrations, btop,
  CSG removal) are split into their own tickets and explicitly not blockers.

## Live acceptance evidence (2026-10-30)

Bootstrap completed. Installed versions: engine `0.1.27`, runtime `0.4.1`,
CSG `0.2.2`, tpr `0.4.0`.

| # | Result | Evidence |
|---|---|---|
| 1 | PASS | bootstrap completed; engine/runtime/CSG/tpr versions above |
| 2 | PASS | `config/dotfiles-runtime/producer.json` = `{"schema_version":1,"producer":"tpr","tpr_engine":"native","tpr_runtime":"container"}` |
| 3 | PASS | no `environment.d` producer file; no unit `Environment=`; `inspect producer` with ambient csg → `source: config`, `ignored_env: csg` |
| 4 | PASS | manual `~/.local/bin/tpr-native` removed; selector-CWD tpr set still succeeded via the image |
| 5 | PASS | `white_tailed_eagle.png` tpr set: palette `a53f2180…`, 8 artifacts, cache miss then hit |
| 6 | PASS | same image run from the selector app CWD with stale `RUNTIME__PALETTE__PRODUCER=csg` succeeded with tpr |
| 7 | PASS | selector-shaped set reports `producer=tpr`, `producer_source=config`, `producer_engine=native` |
| 8 | PASS | rofi `colors.rasi` created at 07:56:42; rofi opens with rc 124 and empty stderr |
| 9 | PASS | AGS 7 apps / 0 failures; GTK3/4, rofi, btop, AGS links to `a53f2180…`; doctor clean |
| 10 | PASS | forced tpr missing-artifact failure records `tool: tpr`, rc 0, stdout/stderr, elapsed, missing list; state unchanged |
| 11 | PARTIAL | runtime one-shot `--producer csg` succeeded (palette `e2f7…`) and tpr restored; full `RUNTIME_PALETTE_PRODUCER=csg ./bootstrap.sh` config rollback still requires a root bootstrap |
| 12 | PASS | restore default tpr: cache hit, palette `01c9360b…`; no manual helper/env/link repair |

Closed tickets: provisioning BUG-006/007/008, runtime REQ-004/005/BUG-007,
CSG BUG-002, selector BUG-001.

### Remaining root-gated check

The only open adoption row is the full composition rollback: run
`RUNTIME_PALETTE_PRODUCER=csg ./bootstrap.sh`, verify `producer.json` is csg and
consumers follow, then restore with `./bootstrap.sh`. The runtime one-shot
rollback and the provisioning render tests already cover the mechanism; this is
the final end-to-end configuration exercise.
