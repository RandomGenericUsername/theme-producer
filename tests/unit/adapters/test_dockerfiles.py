"""Structural checks for the pinned container images (REQ-011).

These are pure text assertions: no container engine and no network. The live
build/smoke checks live in ``tests/integration/test_image_smoke.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCKER_DIR = ROOT / "src" / "theme_producer" / "adapters" / "docker"
BASE = DOCKER_DIR / "Dockerfile.base"
MATUGEN = DOCKER_DIR / "Dockerfile.matugen"

MATUGEN_VERSION = "4.2.0"
MATUGEN_SHA256 = "a2e3b50e49ed6439999ba3c252ed04fabd98ee4e9d12e5e5dff2e66370569751"
MATUGEN_RELEASE_URL = (
    "https://github.com/InioX/matugen/releases/download/"
    f"v{MATUGEN_VERSION}/matugen-{MATUGEN_VERSION}-x86_64.tar.gz"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["Dockerfile.base", "Dockerfile.matugen"])
def test_dockerfile_exists(name: str) -> None:
    assert (DOCKER_DIR / name).is_file()


def _first_instruction(path: Path) -> str:
    for line in read(path).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    raise AssertionError(f"{path.name} has no instructions")


def test_base_is_pinned_to_python_314_slim() -> None:
    assert _first_instruction(BASE) == "FROM python:3.14-slim"


def test_base_installs_git_ca_certificates_and_pinned_uv() -> None:
    text = read(BASE)
    assert "apt-get install -y --no-install-recommends git ca-certificates" in text
    assert 'pip install --no-cache-dir "uv==0.9.22"' in text


def test_base_sets_the_documented_uv_environment() -> None:
    text = read(BASE)
    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in text
    assert "UV_LINK_MODE=copy" in text
    assert "UV_PYTHON_DOWNLOADS=never" in text


def test_base_copies_only_in_repo_paths_and_syncs_the_frozen_lock() -> None:
    text = read(BASE)
    assert "COPY pyproject.toml uv.lock README.md LICENSE ./" in text
    assert "COPY src ./src" in text
    assert "uv sync --frozen --no-dev --no-editable" in text


def test_base_has_the_unprivileged_home_and_entrypoint() -> None:
    text = read(BASE)
    assert "/home/tpruser" in text
    assert "chmod 777 /home/tpruser" in text
    assert 'PATH="/opt/venv/bin:$PATH"' in text
    assert "HOME=/home/tpruser" in text
    assert 'CMD ["sleep", "infinity"]' in text


def test_base_build_context_is_this_repository_root() -> None:
    text = read(BASE)
    assert "WORKDIR /app" not in text
    assert "../" not in text


def test_matugen_image_derives_from_the_base_argument() -> None:
    text = read(MATUGEN)
    assert "ARG BASE_IMAGE=tpr-base-docker:latest" in text
    assert "FROM ${BASE_IMAGE}" in text


def test_matugen_downloads_the_pinned_release_and_verifies_the_checksum() -> None:
    text = read(MATUGEN)
    assert MATUGEN_RELEASE_URL in text
    assert MATUGEN_SHA256 in text
    assert "sha256sum -c -" in text
    # No pipe into tar/install: the archive is verified before it is extracted.
    assert "| tar" not in text
    assert "curl -fsSL -o /tmp/matugen.tar.gz" in text
    assert "tar -xzf /tmp/matugen.tar.gz -C /tmp matugen" in text
    assert "install -m 0755 /tmp/matugen /usr/local/bin/matugen" in text


def test_matugen_image_ships_the_gpl_notice_and_source_reference() -> None:
    text = read(MATUGEN)
    assert f"https://raw.githubusercontent.com/InioX/matugen/v{MATUGEN_VERSION}/LICENSE" in text
    assert "/usr/share/doc/matugen/LICENSE" in text
    assert "/usr/share/doc/matugen/SOURCE" in text
    assert f"tag: v{MATUGEN_VERSION}" in text
    assert "https://github.com/InioX/matugen" in text


def test_matugen_image_declares_the_oci_license_and_source_labels() -> None:
    text = read(MATUGEN)
    assert 'org.opencontainers.image.licenses="GPL-2.0-or-later"' in text
    assert (
        f'org.opencontainers.image.source="https://github.com/InioX/matugen/tree/v{MATUGEN_VERSION}"'
        in text
    )


def test_matugen_image_fails_the_build_when_the_binary_is_missing() -> None:
    text = read(MATUGEN)
    assert "matugen --version" in text


@pytest.mark.parametrize("path", [BASE, MATUGEN], ids=["base", "matugen"])
def test_no_dockerfile_references_a_path_outside_this_repo(path: Path) -> None:
    text = read(path)
    assert "../" not in text
    assert "color-scheme-generator" not in text
    for line in text.splitlines():
        if re.match(r"^\s*(COPY|ADD)\s", line):
            for source in line.split()[1:-1]:
                assert not source.startswith("/"), f"absolute COPY source: {source}"


def test_dockerignore_keeps_the_context_to_repo_content() -> None:
    ignore = read(ROOT / ".dockerignore")
    for entry in (".git", ".venv", ".worktrees", "dist", "build", "tests", "**/__pycache__"):
        assert entry in ignore


def test_makefile_builds_both_images_at_the_pyproject_version() -> None:
    makefile = read(ROOT / "Makefile")
    assert "IMAGE_ENGINE ?= podman" in makefile
    assert "IMAGE_TAG    ?= v$(VERSION)" in makefile
    assert "IMAGE_PREFIX ?= tpr" in makefile
    assert "THEME_ENGINES = matugen" in makefile
    assert "BASE_IMAGE    = $(IMAGE_PREFIX)-base-$(IMAGE_ENGINE):$(IMAGE_TAG)" in makefile
    assert "Dockerfile.base" in makefile
    assert "Dockerfile.$$engine" in makefile
    assert "--build-arg BASE_IMAGE=" in makefile
    assert "tpr version" in makefile
    assert "matugen --version" in makefile
    assert re.search(r"^GATES := test lint hermetic lock-check docs-check$", makefile, re.MULTILINE)
