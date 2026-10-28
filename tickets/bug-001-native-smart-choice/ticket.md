---
id: BUG-001
title: "Native engine advertises scheme-smart but rejects it"
kind: bug
status: done
lane: 1 — XS direct
severity: medium
links:
  openspec: none
  bmad: none
worktree: .worktrees/bug-001/
branch: ticket/bug-001-release-hygiene
repro: "PATH=native/target/release:$PATH uv run tpr generate /tmp/img.png --engine native --param scheme_type=scheme-smart -o /tmp/out"
observed: "tpr-native exits non-zero: unsupported scheme scheme-smart"
expected: "The native catalog does not offer scheme-smart; the CLI rejects it with a choices error listing the 9 supported schemes. Matugen keeps scheme-smart."
---

# Native engine advertises scheme-smart but rejects it

## Repro

`PATH=native/target/release:$PATH uv run tpr generate /tmp/img.png --engine native --param scheme_type=scheme-smart -o /tmp/out`

## Observed

`tpr-native` exits non-zero with an unsupported-scheme error after the CLI accepted the param.

## Expected

The native `engines.yaml` entry lists only the nine Material variants the helper implements; the CLI
rejects `scheme-smart` for native with a clear choices error. The matugen entry keeps ten.

## Fix notes

Remove `scheme-smart` from the native choices; update tests (catalog + CLI param choice) and the
native README. Regression: a native `--param scheme_type=scheme-smart` exits with the choices error,
not the helper's error.
