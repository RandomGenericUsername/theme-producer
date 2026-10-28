---
id: REQ-011
title: "Pinned base + matugen images, install/uninstall"
kind: requirement
status: in-progress
lane: 3 — ticket-multi
parent: EPIC-001
links:
  openspec: req-011-container-images
  bmad: none
worktree: .worktrees/req-011/
branch: ticket/req-011-container-images
---

# Pinned base + matugen images, install/uninstall

## Requirement

Build and manage the container images through `oci-runtime`, with the tag as the pin.

## Acceptance

- [ ] `Dockerfile.base` (python:3.14-slim + uv sync) and `Dockerfile.matugen` (pinned 4.2.0 release
      **and checksum**; GPL notice + source reference).
- [ ] `install` builds base + selected engines; `uninstall` removes; `list-engines` reports host and
      image availability; `make image` builds at `v<version>` and runs `tpr version` in the base.
- [ ] `ContainerProcessor` mounts input/output/config/templates and runs `tpr generate --runtime
      local` inside the image; no host cache.
- [ ] `--dry-run` pre-flights engine/image/templates without executing.
- [ ] Engine tests skip honestly when no engine is reachable.
- [ ] `make image` and `make gates` green.

## Done-when

`make image` builds and smoke-runs; `tpr install --dry-run` and `tpr list-engines` are green.

