"""Oracle parity: the native helper and matugen on the same seed.

Both engines are invoked as external processes with the same `#ff0000` seed,
tonal-spot scheme, and contrast. Every role in both modes and every tone in all
six palettes must match exactly. This is the claim REQ-013 makes: the v2 engine
uses the same `material-colors` generator matugen 4.2.0 wraps, so no tolerance
is needed for the deterministic color path.

The test skips honestly when either binary is absent; the reason names both
binaries and the command that installs/builds them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from theme_producer.domain.enums import MaterialRole, PaletteName, TONE_ORDER

MATUGEN = shutil.which("matugen")
NATIVE = shutil.which("tpr-native")
_MISSING = [
    name
    for name, path in (("matugen", MATUGEN), ("tpr-native", NATIVE))
    if path is None
]

pytestmark = pytest.mark.skipif(
    bool(_MISSING),
    reason=(
        f"engine parity needs both binaries on PATH; missing: {', '.join(_MISSING)}. "
        "Install matugen 4.2.0 and build native/ "
        "(`cd native && cargo build --release --locked`), then put "
        "`native/target/release` on PATH."
    ),
)

MINIMAL_CONFIG = "[config]\n\n[templates]\n"
SEED = "#ff0000"
SCHEME = "scheme-tonal-spot"
CONTRAST = "0"


def _run(argv: list[str], *, timeout: int = 120) -> str:
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    assert result.returncode == 0, (
        f"{argv[0]} exited {result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result.stdout


def _matugen_payload(tmp_path: Path) -> dict[str, Any]:
    config = tmp_path / "matugen.toml"
    config.write_text(MINIMAL_CONFIG, encoding="utf-8")
    stdout = _run(
        [
            MATUGEN or "matugen",
            "color",
            "hex",
            SEED,
            "--json",
            "hex",
            "--dry-run",
            "--mode",
            "dark",
            "--type",
            SCHEME,
            "--contrast",
            CONTRAST,
            "--config",
            str(config),
            "--quiet",
        ]
    )
    return json.loads(stdout)


def _native_payload() -> dict[str, Any]:
    stdout = _run(
        [
            NATIVE or "tpr-native",
            "--color",
            SEED,
            "--scheme",
            SCHEME,
            "--contrast",
            CONTRAST,
            "--json",
        ]
    )
    return json.loads(stdout)


def _matugen_roles(payload: dict[str, Any], mode: str) -> dict[str, str]:
    return {
        role: payload["colors"][role][mode]["color"]
        for role in (entry.value for entry in MaterialRole)
    }


def _matugen_palettes(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        palette: {
            str(tone): payload["palettes"][palette][str(tone)]["color"]
            for tone in TONE_ORDER
        }
        for palette in (entry.value for entry in PaletteName)
    }


def test_native_matches_matugen_for_every_role_and_tone(tmp_path: Path) -> None:
    matugen = _matugen_payload(tmp_path)
    native = _native_payload()

    assert native["schema_version"] == "1"
    assert native["generator"] == {
        "engine": "native",
        "engine_version": "0.1.0",
        "schema_version": "1",
    }
    assert native["scheme"] == SCHEME
    assert native["contrast"] == 0.0
    assert native["source"] == {
        "kind": "color",
        "path": None,
        "hash": native["source"]["hash"],
    }

    expected_palettes = _matugen_palettes(matugen)
    for mode in ("dark", "light"):
        expected_roles = _matugen_roles(matugen, mode)
        actual = native["modes"][mode]

        assert len(expected_roles) == 50
        assert set(expected_roles) == {role.value for role in MaterialRole}
        assert actual["roles"] == expected_roles

        actual_palettes = actual["palettes"]
        assert set(actual_palettes) == {palette.value for palette in PaletteName}
        assert all(len(tones) == 18 for tones in actual_palettes.values())
        assert actual_palettes == expected_palettes


def test_native_matches_matugen_at_nonzero_contrast(tmp_path: Path) -> None:
    matugen_config = tmp_path / "matugen-contrast.toml"
    matugen_config.write_text(MINIMAL_CONFIG, encoding="utf-8")
    matugen = json.loads(
        _run(
            [
                MATUGEN or "matugen",
                "color",
                "hex",
                SEED,
                "--json",
                "hex",
                "--dry-run",
                "--mode",
                "dark",
                "--type",
                SCHEME,
                "--contrast",
                "0.5",
                "--config",
                str(matugen_config),
                "--quiet",
            ]
        )
    )
    native = json.loads(
        _run(
            [
                NATIVE or "tpr-native",
                "--color",
                SEED,
                "--scheme",
                SCHEME,
                "--contrast",
                "0.5",
                "--json",
            ]
        )
    )

    for mode in ("dark", "light"):
        assert native["modes"][mode]["roles"] == _matugen_roles(matugen, mode)
        assert native["modes"][mode]["palettes"] == _matugen_palettes(matugen)
