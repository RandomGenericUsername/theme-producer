# Ticket index

> Counting rule: completeness checks cover item files (`tickets/<id>-<slug>/ticket.md`) only.
> `tickets/_template/` and `tickets/_fixtures/` are excluded. Entry format: link — title |
> `status` | execution links. Epics add `done/total children done`, done-when, and one nested
> line per child. Spikes add timebox state.

## Epics

- [epic-001-theme-producer](./epic-001-theme-producer/ticket.md) — Theme producer (successor to CSG) | `in-progress` | 23/26 complete (22 done + 1 spike reported; REQ-014 blocked, REQ-020/021 pending) | done-when: a pinned `tpr` release produces a schema-valid Theme + eight projections; adoption spike reports a mechanical CSG swap; gates + image smoke green | exec: bmad brief+spec+spine
  - [ops-001-repo-birth](./ops-001-repo-birth/ticket.md) — Repo birth + planning substrate | `done`
  - [req-001-product-brief](./req-001-product-brief/ticket.md) — Product brief | `done`
  - [req-002-spec](./req-002-spec/ticket.md) — Spec (CAP-001..012) | `done`
  - [req-003-architecture-spine](./req-003-architecture-spine/ticket.md) — Architecture spine (AD-1..13) | `done`
  - [req-004-repo-harness](./req-004-repo-harness/ticket.md) — Executable harness: packaging, gates, CI, hermetic tests | `done`
  - [req-005-domain-theme-model](./req-005-domain-theme-model/ticket.md) — Theme domain model + alias vocabulary | `done`
  - [req-006-settings](./req-006-settings/ticket.md) — Settings via config-assembler-engine | `done`
  - [req-007-engines](./req-007-engines/ticket.md) — ThemeEnginePort + matugen engine + engines.yaml | `done`
  - [req-008-projections](./req-008-projections/ticket.md) — Canonical theme.json + open projections | `done`
  - [req-009-ansi-projection](./req-009-ansi-projection/ticket.md) — ANSI intent projection (kitty, sequences) | `done`
  - [req-010-cli](./req-010-cli/ticket.md) — CLI surface + local/container/dry-run processors | `done`
  - [req-011-container-images](./req-011-container-images/ticket.md) — Pinned base + matugen images, install/uninstall | `done`
  - [req-012-invocation-contract](./req-012-invocation-contract/ticket.md) — contracts record + conformance test | `done`
  - [req-013-native-engine](./req-013-native-engine/ticket.md) — v2 Rust helper on material-colors + oracle parity | `done`
  - [bug-001-native-smart-choice](./bug-001-native-smart-choice/ticket.md) — Native engine advertises scheme-smart but rejects it | `done` | severity: medium
  - [bug-002-image-tag-latest](./bug-002-image-tag-latest/ticket.md) — Default container image_tag is latest, not the pin | `done` | severity: medium
  - [req-014-dotfiles-adoption](./req-014-dotfiles-adoption/ticket.md) — Dotfiles runtime/provisioning adoption (after spike) | `proposed`
  - [req-015-native-source-parity](./req-015-native-source-parity/ticket.md) — Native source-color parity: prefer + fallback_color | `done` | known: 41/56 exact, 15 recorded deltas
  - [req-016-native-lightness-controls](./req-016-native-lightness-controls/ticket.md) — Native lightness controls: lightness_dark / lightness_light | `done` | 2500/2500 within ±1
  - [req-017-light-mode-projections](./req-017-light-mode-projections/ticket.md) — Light-mode projections: --mode dark|light | `done`
  - [req-018-smart-mode](./req-018-smart-mode/ticket.md) — Smart projection mode: --mode smart (configurable) | `done`
  - [bug-003-legacy-token-compat](./bug-003-legacy-token-compat/ticket.md) — GTK/rasi legacy tokens missing (AGS/rofi break) | `done` | severity: high | fixed v0.3.1
  - [req-019-scheme-policy-domain](./req-019-scheme-policy-domain/ticket.md) — Scheme policy domain: metrics, rules, resolver | `done`
  - [req-020-scheme-policy-catalog](./req-020-scheme-policy-catalog/ticket.md) — Scheme policy catalog + metrics adapters | `in-progress`
  - [req-021-scheme-policy-integration](./req-021-scheme-policy-integration/ticket.md) — Scheme policy integration: scheme-smart resolution | `proposed`

  - [spike-001-dotfiles-fit](./spike-001-dotfiles-fit/ticket.md) — Dotfiles fit: adapter, hashes, contract, rollout | `reported` | timebox 4h

## Standalone requirements

(none — all items are children of EPIC-001)

## Bugs

(none)

## Ops

(covered under EPIC-001)

