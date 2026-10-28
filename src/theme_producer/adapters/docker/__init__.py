"""Dockerfile path helpers for the install/uninstall verbs.

REQ-011 owns the actual ``Dockerfile.base`` / ``Dockerfile.<engine>`` files and
the Makefile ``image`` target. This module only names their expected locations
so the install code path exists and can fail clearly while they are absent.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["BASE_DOCKERFILE_NAME", "docker_dir", "dockerfile_path"]

BASE_DOCKERFILE_NAME = "Dockerfile.base"


def docker_dir() -> Path:
    """Return the directory that owns the engine Dockerfiles."""
    return Path(__file__).resolve().parent


def dockerfile_path(engine: str) -> Path:
    """Return the expected Dockerfile path for ``engine`` or ``base``."""
    name = engine.strip()
    if not name:
        raise ValueError("engine must be a non-empty name")
    if name == "base":
        return docker_dir() / BASE_DOCKERFILE_NAME
    return docker_dir() / f"Dockerfile.{name}"
