# Ticket index

> Counting rule: completeness checks cover item files (`tickets/<id>-<slug>/ticket.md`) only.
> `tickets/_template/` and `tickets/_fixtures/` are excluded. Entry format: link — title |
> `status` | execution links. Epics add `done/total children done`, done-when, and one nested
> line per child. Spikes add timebox state.

## Epics

- [epic-001-theme-producer](./epic-001-theme-producer/ticket.md) — Theme producer (successor to CSG) | `in-progress` | 5/16 children done | done-when: a pinned `tpr` release produces a schema-valid Theme + eight projections; adoption spike reports a mechanical CSG swap; gates + image smoke green | exec: bmad brief+spec+spine
  - [ops-001-repo-birth](./ops-001-repo-birth/ticket.md) — Repo birth + planning substrate | `done`
  - [req-001-product-brief](./req-001-product-brief/ticket.md) — Product brief | `done`
  - [req-002-spec](./req-002-spec/ticket.md) — Spec (CAP-001..012) | `done`
  - [req-003-architecture-spine](./req-003-architecture-spine/ticket.md) — Architecture spine (AD-1..13) | `done`
  - [req-004-repo-harness](./req-004-repo-harness/ticket.md) — Executable harness: packaging, gates, CI, hermetic tests | `done`
  - [req-005-domain-theme-model](./req-005-domain-theme-model/ticket.md) — Theme domain model + alias vocabulary | `in-progress`
  - [req-006-settings](./req-006-settings/ticket.md) — Settings via config-assembler-engine | `in-progress`
  - [req-007-engines](./req-007-engines/ticket.md) — ThemeEnginePort + matugen engine + engines.yaml | `proposed`
  - [req-008-projections](./req-008-projections/ticket.md) — Canonical theme.json + open projections | `proposed`
  - [req-009-ansi-projection](./req-009-ansi-projection/ticket.md) — ANSI intent projection (kitty, sequences) | `proposed`
  - [req-010-cli](./req-010-cli/ticket.md) — CLI surface + local/container/dry-run processors | `proposed`
  - [req-011-container-images](./req-011-container-images/ticket.md) — Pinned base + matugen images, install/uninstall | `proposed`
  - [req-012-invocation-contract](./req-012-invocation-contract/ticket.md) — contracts record + conformance test (blocked) | `proposed`
  - [req-013-native-engine](./req-013-native-engine/ticket.md) — v2 Rust helper on material-colors + oracle parity | `proposed`
  - [req-014-dotfiles-adoption](./req-014-dotfiles-adoption/ticket.md) — Dotfiles runtime/provisioning adoption (after spike) | `proposed`
  - [spike-001-dotfiles-fit](./spike-001-dotfiles-fit/ticket.md) — Dotfiles fit: adapter, hashes, contract, rollout | `boxed` | timebox 4h

## Standalone requirements

(none — all items are children of EPIC-001)

## Bugs

(none)

## Ops

(covered under EPIC-001)

