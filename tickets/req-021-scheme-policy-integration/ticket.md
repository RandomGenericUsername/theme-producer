---
id: REQ-021
title: "Scheme policy integration: scheme-smart resolution"
kind: requirement
status: done
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: .worktrees/req-021/
branch: ticket/req-021-scheme-policy-integration
---

# Scheme policy integration: scheme-smart resolution

## Requirement

Wire `scheme-smart` through `generate`/`show` per `docs/SCHEME-POLICY.md`.

Precedence and defaults (must preserve today's output):

1. `--param scheme_type=<real variant>` wins.
2. `[generation] scheme_type` (new setting, default `scheme-tonal-spot`) selects the variant.
3. `scheme_type=scheme-smart` (from either source) runs the policy:
   load `scheme-policies.yaml`, measure metrics, resolve a real variant, pass that to the engine.
4. `[generation] scheme_policy` (default `balanced`) selects the profile; `--scheme-policy`
   overrides it; `--policies-file` selects the catalog.
5. `scheme_policy` alone must NOT enable smart; only `scheme_type=scheme-smart` does.

Behavior:

- Metrics: `PillowImageMetrics` on the image (or seed color). JSON + smart fails clearly.
- Resolve on the host; the container inner command receives the concrete variant.
- `theme.json.scheme` records the concrete variant.
- `--dry-run` prints metrics, profile and chosen variant.
- `info`/`dump-config` report `scheme_type`, `scheme_policy`, and the resolved catalog path.
- CLI: `--scheme-policy <profile>` and `--policies-file <path>` on `generate`/`show`
  (or global if cleaner); `--param scheme_type=scheme-smart` must be accepted even though native's
  engine catalog only lists the nine real variants.
- Calibrate on the seven real wallpapers: print the metrics → variant table for each built-in
  profile; adjust thresholds or the colorfulness normalizer if the picks are poor. Update
  `docs/SCHEME-POLICY.md` (`defaults/scheme-policies.yaml`) with the measured table and any
  threshold changes.

## Acceptance

- [ ] `scheme_type=scheme-smart` works with matugen and native; both pass the concrete variant.
- [ ] Explicit real `scheme_type` bypasses the policy; default `scheme-tonal-spot` output is
  unchanged.
- [ ] `--scheme-policy` / `--policies-file` / settings/env select profile and catalog.
- [ ] Dry-run shows metrics/profile/variant; container receives the concrete variant; `theme.json`
  matches.
- [ ] JSON source + smart fails with a typed error; color source uses its metrics.
- [ ] Corpus table recorded; thresholds calibrated if needed.
- [ ] `make gates` green; no dotfiles changes; existing artifacts unchanged.

## Evidence

- `docs/SCHEME-POLICY.md` AD-5/AD-6.
- `REQ-019` domain/resolver, `REQ-020` metrics/catalog/settings.