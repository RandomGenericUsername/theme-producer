"""Prove this repo's own half of the `tpr` invocation contract (AD-4) in CI.

The contract (`cli_invocation_contract.invocation-contract.json`) owns the argv,
the env keys and the artifact list. This test owns **execution only**: it runs
the installed `tpr` console script with the record's argv, a scrubbed
environment and a temp output directory, then delegates the assertion to
``assert_cli_writes_artifacts`` from the pinned conformance kit.

Two documented settings overrides are injected on top of the record's own env
values:

- ``THEME__GENERATION__ENGINE=native`` — the record's argv deliberately carries
  no ``--engine``. The native helper is the binary built from this checkout, so
  the test proves this repo's engine, not a host-wide default.
- ``THEME__RUNTIME__MODE=local`` — pins generation in-process, so a stray host
  ``settings.toml`` cannot switch the run to container mode and demand an
  image/network.

``tpr generate`` also writes the canonical ``theme.json``. It is intentionally
not part of the record (the runtime cache accepts only the eight consumer
files), so this test asserts it as an *extra* artifact.

The test skips honestly when no engine binary is available; the reason names
both binaries and the command that builds the native helper. It never fakes a
successful run.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

import pytest
from cli_invocation_contract import get
from cli_invocation_contract.testkit import assert_cli_writes_artifacts

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NATIVE_RELEASE = _REPO_ROOT / "native" / "target" / "release"
_PLACEHOLDER = re.compile(r"^\{([a-z0-9_]+)\}\??$")

_WALLPAPER = "wallpaper.png"
_THEME_JSON = "theme.json"


def _native_dir() -> Path | None:
    """Return the directory holding ``tpr-native``, preferring this checkout."""
    if (_NATIVE_RELEASE / "tpr-native").is_file():
        return _NATIVE_RELEASE
    found = shutil.which("tpr-native")
    return Path(found).parent if found is not None else None


_NATIVE_DIR = _native_dir()
_MATUGEN = shutil.which("matugen")
_ENGINE = "native" if _NATIVE_DIR is not None else "matugen"

pytestmark = pytest.mark.skipif(
    _NATIVE_DIR is None and _MATUGEN is None,
    reason=(
        "the tpr invocation contract needs an engine binary on PATH; missing: "
        "tpr-native and matugen. Build the native helper "
        "(`cd native && cargo build --release --locked`) and add "
        "`native/target/release` to PATH."
    ),
)


def _tpr_executable() -> Path:
    """Locate the console script of *this* interpreter's env first, then PATH.

    The venv sibling wins over PATH on purpose: a host-wide ``tpr`` install may
    be an older version and must not be picked up by a test that claims to
    prove *this* checkout's CLI.
    """
    candidates = (str(Path(sys.executable).with_name("tpr")), shutil.which("tpr"))
    for candidate in candidates:
        if candidate is not None and Path(candidate).is_file():
            return Path(candidate)
    pytest.fail(
        "the `tpr` console script is not on PATH and not next to "
        f"{sys.executable}; run `make sync` first"
    )


def _write_wallpaper(path: Path) -> Path:
    """Write a deterministic 16x16 RGB PNG using only the standard library."""
    width = height = 16
    rows = []
    for y in range(height):
        row = bytearray(b"\x00")  # PNG filter type 0
        for x in range(width):
            row.extend((x * 16, y * 16, (x * y) % 256))
        rows.append(bytes(row))
    raw = b"".join(rows)

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


def _contract_argv(record: dict[str, Any], wallpaper: Path) -> list[str]:
    """Build the record's argv with the wallpaper placeholder substituted."""
    substitutions = {"{wallpaper}": str(wallpaper)}
    argv = [str(_tpr_executable())]
    for token in record["argv"]:
        argv.append(substitutions.get(token, token))
    unresolved = [token for token in argv[1:] if _PLACEHOLDER.match(token)]
    assert not unresolved, (
        f"the tpr record gained placeholder(s) this test does not supply: {unresolved}"
    )
    return argv


def _scrubbed_env(root: Path, output_dir: Path, record: dict[str, Any]) -> dict[str, str]:
    """A minimal env: no host HOME/XDG/spine config leaks into the child."""
    for name in ("home", "config", "cache", "data", "state", "tmp"):
        (root / name).mkdir()

    path_parts = [str(Path(sys.executable).parent)]
    if _NATIVE_DIR is not None:
        path_parts.append(str(_NATIVE_DIR))
    elif _MATUGEN is not None:
        path_parts.append(str(Path(_MATUGEN).parent))
    path_parts.extend(["/usr/bin", "/bin"])

    injected = record["env"]["injected"]
    return {
        "PATH": os.pathsep.join(path_parts),
        "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "XDG_DATA_HOME": str(root / "data"),
        "XDG_STATE_HOME": str(root / "state"),
        "TMPDIR": str(root / "tmp"),
        "NO_COLOR": "1",
        "COLUMNS": "200",
        "PYTHONNOUSERSITE": "1",
        # The record's own injected env values.
        "THEME__OUTPUT__DIRECTORY": str(output_dir),
        "THEME__OUTPUT__OVERWRITE": injected["THEME__OUTPUT__OVERWRITE"],
        # Documented settings overrides: this checkout's engine, in-process runtime.
        "THEME__GENERATION__ENGINE": _ENGINE,
        "THEME__RUNTIME__MODE": "local",
    }


def _runner(
    argv: list[str],
    env: dict[str, str],
    cwd: Path,
    timeout: float,
) -> Any:
    """Return the zero-arg callable the kit runs; fail loudly with output on error."""

    def run() -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            pytest.fail(
                f"tpr exited {completed.returncode}\n"
                f"argv: {argv}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return completed

    return run


def test_tpr_writes_every_artifact_the_contract_requires(tmp_path: Path) -> None:
    record = get("tpr")

    root = tmp_path / "contract"
    output_dir = root / "output"
    output_dir.mkdir(parents=True)
    wallpaper = _write_wallpaper(root / _WALLPAPER)

    env = _scrubbed_env(root, output_dir, record)
    argv = _contract_argv(record, wallpaper)

    artifacts = assert_cli_writes_artifacts(
        record,
        "tpr",
        _runner(argv, env, output_dir, record["timeout"]),
        output_dir,
    )

    expected = len(record["artifacts"]["filenames"])
    assert len(artifacts) == expected == record["artifacts"]["min_count"]
    assert {path.name for path in artifacts} == set(record["artifacts"]["filenames"])
    for path in artifacts:
        assert path.stat().st_size > 0, f"{path.name} is an empty artifact"

    # Canonical output, deliberately outside the record's consumer artifact set.
    assert _THEME_JSON not in record["artifacts"]["filenames"]
    theme_json = output_dir / _THEME_JSON
    assert theme_json.is_file(), "tpr did not write the canonical theme.json"
    assert theme_json.stat().st_size > 0, "theme.json is empty"
