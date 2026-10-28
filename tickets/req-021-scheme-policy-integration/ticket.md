---
id: REQ-021
title: "Scheme policy integration: scheme-smart resolution"
kind: requirement
status: proposed
lane: 3
links:
  openspec: none
  bmad: architecture-theme-producer
worktree: none
branch: none
---

# Scheme policy integration: scheme-smart resolution

## Requirement

Wire `scheme-smart` through `generate`/`show` per `docs/SCHEME-POLICY.md`:

- Resolve metrics + policy on the host, then call the engine with the concrete variant.
- Explicit real `scheme_type` bypasses the policy; `scheme_type=scheme-smart` runs it; settings
  `scheme_policy` selects the profile.
- Accept `scheme-smart` as a `tpr` pseudo-value for both engines; native's catalog does not need to
  advertise it.
- `--dry-run` prints metrics, profile and chosen variant; container inner command receives the
  concrete variant; `theme.json.scheme` records it.
- `info`/`dump-config` report the policy catalog and profile.
- Docs update (`docs/SCHEME-POLICY.md` status, README).
- Corpus run: seven real wallpapers, record metrics → chosen variant.

## Acceptance

- [ ] `--param scheme_type=scheme-smart` works with matugen and native.
- [ ] `--scheme-policy balanced|vivid|muted|source-faithful` works; `--policies-file` override.
- [ ] Explicit `scheme_type` wins over the policy.
- [ ] Dry-run shows metrics/profile/variant; container receives the concrete variant; `theme.json`
  matches.
- [ ] No new artifacts; existing dark/light/prefer/lightness tests unchanged.
- [ ] `make gates` green; corpus table recorded.

## Evidence

- `docs/SCHEME-POLICY.md` AD-5/AD-6.
- REQ-019/REQ-020 artifacts.
