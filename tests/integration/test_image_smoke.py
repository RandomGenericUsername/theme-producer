"""Live smoke tests for the pinned base + matugen images (REQ-011).

They never fake a result:

* the tests are opt-in (``TPR_IMAGE_SMOKE=1``) so ``make gates`` stays hermetic
  and fast; the skip reason names the exact command that runs them;
* no container engine on PATH -> skip with that reason;
* the engine cannot see the built image (different rootless store, or not built)
  -> skip with the exact ``make image`` command that builds it;
* otherwise the test runs the real image: ``tpr version`` in the base, the
  pinned matugen version and its GPL notice in the engine image, and a real
  ``tpr generate`` inside the matugen image against a generated PNG.

``tests/conftest.py`` isolates ``HOME``/``XDG_*`` for every test, so a rootless
engine would look at an empty store. The engine subprocesses deliberately get
the invoking user's real ``HOME`` back: this file tests the host engine, not a
hermetic code path.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from pwd import getpwuid

import pytest

from theme_producer import __version__

ENGINES = ("podman", "docker")
OPT_IN_ENV = "TPR_IMAGE_SMOKE"
PINNED_MATUGEN_VERSION = "4.2.0"
_TAG = f"v{__version__}"
BASE_IMAGE = f"tpr-base-{{engine}}:{_TAG}"
MATUGEN_IMAGE = f"tpr-matugen-{{engine}}:{_TAG}"


def _opted_in() -> bool:
    return os.environ.get(OPT_IN_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _engine_name() -> str | None:
    requested = os.environ.get("IMAGE_ENGINE", "").strip()
    candidates = (requested,) if requested else ENGINES
    for candidate in candidates:
        if candidate and shutil.which(candidate):
            return candidate
    return None


def _engine_environment() -> dict[str, str]:
    """The invoking user's engine store, not the test's isolated ``HOME``."""
    env = dict(os.environ)
    home = Path(getpwuid(os.getuid()).pw_dir)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["XDG_DATA_HOME"] = str(home / ".local" / "share")
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    env["XDG_STATE_HOME"] = str(home / ".local" / "state")
    return env


def _run(engine: str, args: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [engine, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=_engine_environment(),
    )


def _user_namespace(engine: str) -> list[str]:
    """Mirror the production adapter: podman runs with ``--userns=keep-id``."""
    return ["--userns=keep-id"] if engine == "podman" else []


@pytest.fixture(scope="module")
def engine() -> str:
    if not _opted_in():
        pytest.skip(
            "container image smoke tests are opt-in; build with "
            "`make image IMAGE_ENGINE=<engine>` then run "
            f"`{OPT_IN_ENV}=1 uv run pytest tests/integration/test_image_smoke.py`"
        )
    name = _engine_name()
    if name is None:
        pytest.skip(
            "no container engine on PATH (tried podman, docker); "
            "set IMAGE_ENGINE=<engine> or skip the image smoke tests"
        )
    return name


def _require_image(engine: str, template: str) -> str:
    image = template.format(engine=engine)
    try:
        result = _run(engine, ["image", "inspect", image], timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - engine broken
        pytest.skip(f"container engine {engine!r} is not usable here: {exc}")
    if result.returncode != 0:
        pytest.skip(
            f"image {image!r} is not visible to {engine!r}; build it with "
            f"`make image IMAGE_ENGINE={engine}` (or it lives in another store)"
        )
    return image


def _write_png(path: Path, width: int = 16, height: int = 16) -> Path:
    """Write a minimal solid-green PNG with only the standard library."""
    pixel = bytes((0x2E, 0x7D, 0x32))
    raw = b"".join(b"\x00" + pixel * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return path


def test_base_image_runs_the_cli(engine: str) -> None:
    image = _require_image(engine, BASE_IMAGE)

    result = _run(engine, ["run", "--rm", image, "tpr", "version"], timeout=120)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == __version__


def test_matugen_image_reports_the_pinned_version(engine: str) -> None:
    image = _require_image(engine, MATUGEN_IMAGE)

    result = _run(engine, ["run", "--rm", image, "matugen", "--version"], timeout=120)

    assert result.returncode == 0, result.stderr
    assert "matugen" in result.stdout
    assert PINNED_MATUGEN_VERSION in result.stdout


def test_matugen_image_ships_its_license_and_source(engine: str) -> None:
    image = _require_image(engine, MATUGEN_IMAGE)

    result = _run(
        engine,
        [
            "run",
            "--rm",
            image,
            "sh",
            "-c",
            "test -s /usr/share/doc/matugen/LICENSE && "
            "grep -q 'GNU GENERAL PUBLIC LICENSE' /usr/share/doc/matugen/LICENSE && "
            f"grep -q 'v{PINNED_MATUGEN_VERSION}' /usr/share/doc/matugen/SOURCE",
        ],
        timeout=120,
    )

    assert result.returncode == 0, result.stderr


def test_matugen_image_generates_a_theme(engine: str, tmp_path: Path) -> None:
    image = _require_image(engine, MATUGEN_IMAGE)
    source = _write_png(tmp_path / "seed.png")
    output = tmp_path / "output"
    output.mkdir()

    result = _run(
        engine,
        [
            "run",
            "--rm",
            *_user_namespace(engine),
            "-u",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{source.parent}:/input:ro",
            "-v",
            f"{output}:/output",
            "-e",
            "HOME=/tmp",
            image,
            "tpr",
            "--output-format",
            "json",
            "generate",
            f"/input/{source.name}",
            "--engine",
            "matugen",
            "--runtime",
            "local",
            "--no-summary",
            "-o",
            "/output",
            "--format",
            "yaml",
        ],
        timeout=300,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert (output / "theme.json").is_file()
    assert (output / "colors.yaml").is_file()
    theme = json.loads((output / "theme.json").read_text(encoding="utf-8"))
    assert theme["generator"]["engine"] == "matugen"
    assert theme["generator"]["engine_version"] == PINNED_MATUGEN_VERSION
