---
id: REQ-019
title: "Scheme policy domain: metrics, rules, resolver"
kind: requirement
status: in-progress
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-019/
branch: ticket/req-019-scheme-policy-domain
---

# Scheme policy domain: metrics, rules, resolver

## Requirement

Implement the pure hexagonal core for `scheme-smart` per `docs/SCHEME-POLICY.md`:

- `SchemeVariant` (nine real Material variants).
- `ImageMetrics` (saturation, colorfulness, lightness, contrast, hue_diversity; 0..1).
- `MetricName`, `Operator`, `Condition`, `Rule`, `SchemePolicy`, `SchemePolicyCatalog`.
- `SchemePolicyResolver` (first-match, ANDed conditions, per-policy default).
- Validation errors (`SchemePolicyError`) for unknown metric/operator/variant, out-of-range values,
  empty rules, missing default.
- Ports: `ImageMetricsPort`, `SchemePolicyCatalogPort` (Protocols only; no adapters).

No Pillow, YAML, filesystem, CLI or settings in this ticket. Domain stays pure.

## Acceptance

- [ ] Domain modules under `src/theme_producer/domain/scheme_policy.py` (or split enums/models/services)
  with frozen dataclasses and a pure resolver.
- [ ] Every operator (`lt`, `lte`, `gt`, `gte`, `between`) tested; AND semantics; first match wins;
  per-policy default; catalog default profile.
- [ ] Invalid metric/operator/variant, bad ranges, empty rules and missing defaults fail with a
  typed error.
- [ ] Ports are Protocol-only; no adapter imports.
- [ ] `make gates` green; no CLI/settings/engine changes.

## Evidence

- `docs/SCHEME-POLICY.md` AD-1/AD-3/AD-4 and the domain model.
- `src/theme_producer/domain/` existing style.
