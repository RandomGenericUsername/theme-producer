---
id: BUG-002
title: "Default container image_tag is latest, not the pin"
kind: bug
status: in-progress
lane: 1 — XS direct
severity: medium
links:
  openspec: none
  bmad: none
worktree: .worktrees/bug-001/
branch: ticket/bug-001-release-hygiene
repro: "uv run tpr install --dry-run --container-engine podman"
observed: "Plans tpr-base-podman:latest and tpr-matugen-podman:latest by default (settings.container.image_tag = latest)"
expected: "Default resolves to v<package version> (v0.1.0 here); tpr info prints it; make image and tpr install agree."
---

# Default container image_tag is latest, not the pin

## Repro

`uv run tpr install --dry-run --container-engine podman`

## Observed

With the packaged defaults, the planned images are `tpr-base-podman:latest` and
`tpr-matugen-podman:latest`. AD-8 says the tag is the pin, never `latest`.

## Expected

`container.image_tag` defaults to empty and resolves to `v<package version>` (e.g. `v0.1.0`) at
config resolution; `tpr info` prints the resolved tag; `make image` and `tpr install` agree.

## Fix notes

- `defaults/settings.toml`: `image_tag = ""`.
- Settings schema accepts empty; the resolver maps empty -> `v{__version__}` (importlib metadata
  with `__version__` fallback).
- Update tests and README. Regression: `tpr install --dry-run` shows `v0.1.0`, not `latest`.
