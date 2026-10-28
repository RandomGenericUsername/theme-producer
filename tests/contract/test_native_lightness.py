"""Oracle corpus: native ``--lightness-dark`` / ``--lightness-light`` parity.

matugen 4.2.0 is GPL-2.0-or-later and is used ONLY as a black-box oracle here:
the test runs its binary (or the pinned container image) and compares every one
of the 50 roles in both modes with ``tpr-native`` on the same seed, scheme, and
lightness arguments.

The lightness space was identified by probing this oracle, not by reading
matugen's source: all 50 roles, five seeds, both modes, and ``-1..1`` are
reproduced exactly or within ±1 by transforming the **mean of the gamma-encoded
sRGB channels** (HSI intensity) and scaling every sRGB channel by
``target / intensity``:

* dark:  ``target = argument + (1 - argument) * intensity``
* light: ``target = (1 + argument) * intensity``

``source_color`` is never transformed and tonal palettes are untouched; both are
asserted below. A pair may differ by at most :data:`TOLERANCE` units per
channel; anything larger is a material delta and must be recorded in
:data:`KNOWN_DIVERGENCES` (with its exact values) instead of being ignored.

The suite skips with a clear reason when the host wallpapers are absent, the
native helper is missing/stale, or neither matugen nor the pinned image is
reachable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Captured at import time, before tests/conftest.py replaces HOME per test.
_HOST_HOME = Path(os.path.expanduser("~"))
#: The hermetic fixture rewrites HOME/XDG for every test. The oracle needs the
#: real host state only for `podman` (its rootless image store lives under
#: HOME), so subprocesses get this captured environment.
_HOST_ENV = dict(os.environ)
WALLPAPER_DIR = _HOST_HOME / ".local" / "share" / "dotfiles" / "wallpapers"
CACHE_GLOB = ".local/state/dotfiles/cache/wallpapers/*/wallpaper.*"
REPO_ROOT = Path(__file__).resolve().parents[2]

MATUGEN_PROBE = Path("/tmp/opencode/matugen-probe/matugen")
MATUGEN_IMAGE = "localhost/tpr-matugen-podman:v0.1.0"
NATIVE_PROBE = REPO_ROOT / "native" / "target" / "release" / "tpr-native"

SCHEME = "scheme-tonal-spot"
CONTRAST = "0"
MINIMAL_CONFIG = "[config]\n\n[templates]\n"

#: Four pure/neutral primaries plus one seed derived from the wallpaper corpus.
FIXED_SEEDS: tuple[str, ...] = ("#ff0000", "#00ff00", "#0000ff", "#808080")
LIGHTNESS_VALUES: tuple[float, ...] = (-1.0, -0.5, 0.0, 0.5, 1.0)

#: Seven real files from the host wallpaper directory, plus the runtime cache
#: image when it exists. They are read in place and never committed.
WALLPAPERS: tuple[str, ...] = (
    "zenitsu-agatsuma-3840x2160-26517.png",
    "windows-95-dark-3840x2160-27097.jpg",
    "gargantua-black-3840x2160-9621.jpg",
    "japan-artistic-3840x2160-25406.jpg",
    "astronaut-purple-3840x2160-22432.jpg",
    "yasuke-dark-7680x4320-21997.jpg",
    "aurora.jpg",
)

#: A pair may differ by at most this many units per channel. The transform
#: truncates the scaled channel exactly like matugen; the remaining unit is
#: float32-vs-float64 rounding in matugen's own pipeline.
TOLERANCE = 1
#: Beyond this the two engines produced genuinely different colors, not
#: rounding. Nothing is pinned today; the table exists so a regression is
#: recorded instead of hidden.
MATERIAL = 4

#: Recorded material deltas: (seed, value, mode, role) -> (matugen, native).
#: Every entry is asserted exactly and reported as an xfail.
KNOWN_DIVERGENCES: dict[tuple[str, float, str, str], tuple[str, str]] = {}

_ROWS: list[tuple[str, float, str, str, int]] = []


def _podman_images() -> str:
    podman = shutil.which("podman")
    if not podman:
        return ""
    try:
        result = subprocess.run(
            [podman, "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout


def _native_binary() -> str | None:
    on_path = shutil.which("tpr-native")
    if on_path:
        return on_path
    if NATIVE_PROBE.is_file():
        return str(NATIVE_PROBE)
    return None


def _matugen_binary() -> str | None:
    on_path = shutil.which("matugen")
    if on_path:
        return on_path
    if MATUGEN_PROBE.is_file():
        return str(MATUGEN_PROBE)
    return None


def _run(argv: list[str], *, timeout: int = 300) -> str:
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
        env=_HOST_ENV,
    )
    assert result.returncode == 0, (
        f"{argv[0]} exited {result.returncode}\nargv: {argv}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout


def _corpus_wallpaper() -> Path | None:
    for name in WALLPAPERS:
        candidate = WALLPAPER_DIR / name
        if candidate.is_file():
            return candidate
    cached = sorted(_HOST_HOME.glob(CACHE_GLOB))
    return cached[-1] if cached else None


def _matugen_argv(
    *,
    config: Path,
    seed: str | None = None,
    wallpaper: Path | None = None,
    lightness: float | None = None,
) -> list[str]:
    """Build a matugen argv for either the host binary or the pinned image."""
    if wallpaper is not None:
        core = ["image", str(wallpaper)]
    else:
        assert seed is not None
        core = ["color", "hex", seed]
    core.extend(["--json", "hex", "--dry-run", "--mode", "dark"])
    core.extend(["--type", SCHEME, "--contrast", CONTRAST])
    if wallpaper is not None:
        # matugen needs an explicit pick in a non-interactive process.
        core.extend(["--source-color-index", "0"])
    if lightness is not None:
        core.extend(
            [
                "--lightness-dark",
                str(lightness),
                "--lightness-light",
                str(lightness),
            ]
        )

    if MATUGEN is not None:
        return [MATUGEN, *core, "--config", str(config), "--quiet"]

    podman = shutil.which("podman") or "podman"
    argv = [
        podman,
        "run",
        "--rm",
        "--entrypoint",
        "matugen",
        "-v",
        f"{config}:/matugen.toml:ro",
    ]
    if wallpaper is not None:
        argv.extend(["-v", f"{wallpaper}:/wallpaper:ro"])
        core[1] = "/wallpaper"
    argv.extend([MATUGEN_IMAGE, *core, "--config", "/matugen.toml", "--quiet"])
    return argv


def _matugen_payload(
    *,
    seed: str | None = None,
    wallpaper: Path | None = None,
    lightness: float | None = None,
) -> dict[str, Any]:
    descriptor, path = tempfile.mkstemp(prefix="tpr-lightness-", suffix=".toml")
    config = Path(path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_CONFIG)
        return json.loads(
            _run(
                _matugen_argv(
                    config=config, seed=seed, wallpaper=wallpaper, lightness=lightness
                )
            )
        )
    finally:
        config.unlink(missing_ok=True)


def _has_lightness_flags(binary: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
            env=_HOST_ENV,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "--lightness-dark" in result.stdout or "--lightness-dark" in result.stderr


NATIVE = _native_binary()
MATUGEN = _matugen_binary()
HAS_MATUGEN_IMAGE = MATUGEN_IMAGE in _podman_images()
CORPUS_WALLPAPER = _corpus_wallpaper()

_SKIP_REASONS: list[str] = []
if NATIVE is None:
    _SKIP_REASONS.append(
        "tpr-native is missing; run `cd native && cargo build --release --locked` "
        "and add native/target/release to PATH"
    )
elif not _has_lightness_flags(NATIVE):
    _SKIP_REASONS.append(
        "tpr-native is stale (missing --lightness-dark/--lightness-light); rebuild "
        "`cd native && cargo build --release --locked`"
    )
if MATUGEN is None and not HAS_MATUGEN_IMAGE:
    _SKIP_REASONS.append(
        "matugen is missing; install matugen 4.2.0 on PATH, or build/load "
        f"the pinned `{MATUGEN_IMAGE}` image (make image)"
    )
elif MATUGEN is not None and not _has_lightness_flags(MATUGEN):
    _SKIP_REASONS.append(
        "the matugen on PATH predates --lightness-dark/--lightness-light; use "
        f"matugen 4.2.0 or the pinned `{MATUGEN_IMAGE}` image"
    )
if CORPUS_WALLPAPER is None:
    _SKIP_REASONS.append(
        "real wallpapers are absent (expected one of "
        f"{', '.join(WALLPAPERS)} in {WALLPAPER_DIR}); the hermetic gate empties HOME"
    )

#: The fifth seed is matugen's own source color for a real corpus wallpaper,
#: so the corpus seed is not a synthetic value the oracle never sees.
CORPUS_SEED: str | None = None
if not _SKIP_REASONS:
    try:
        _corpus_payload = _matugen_payload(wallpaper=CORPUS_WALLPAPER)
        CORPUS_SEED = _corpus_payload["colors"]["source_color"]["dark"]["color"]
    except (
        AssertionError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ):
        _SKIP_REASONS.append(
            "could not derive a seed color from the wallpaper corpus with matugen"
        )

SEEDS: tuple[str, ...] = (*FIXED_SEEDS, *((CORPUS_SEED,) if CORPUS_SEED else ()))

pytestmark = pytest.mark.skipif(
    bool(_SKIP_REASONS), reason="lightness oracle skipped: " + "; ".join(_SKIP_REASONS)
)


def _max_delta(left: str, right: str) -> int:
    return max(
        abs(int(left[i : i + 2], 16) - int(right[i : i + 2], 16)) for i in (1, 3, 5)
    )


def _native_payload(seed: str, lightness: float) -> dict[str, Any]:
    assert NATIVE is not None
    argv = [
        NATIVE,
        "--color",
        seed,
        "--scheme",
        SCHEME,
        "--contrast",
        CONTRAST,
        "--lightness-dark",
        str(lightness),
        "--lightness-light",
        str(lightness),
        "--json",
    ]
    return json.loads(_run(argv))


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("lightness", LIGHTNESS_VALUES)
def test_roles_match_matugen(seed: str, lightness: float) -> None:
    matugen = _matugen_payload(seed=seed, lightness=lightness)
    native = _native_payload(seed, lightness)

    assert set(native["modes"]["dark"]["roles"]) == set(matugen["colors"])

    for mode in ("dark", "light"):
        for role, node in matugen["colors"].items():
            expected = node[mode]["color"]
            actual = native["modes"][mode]["roles"][role]
            delta = _max_delta(expected, actual)
            _ROWS.append((seed, lightness, mode, role, delta))

            if role == "source_color":
                # The source is echoed, never transformed.
                assert actual == expected, (
                    f"{seed} / {lightness} / {mode}: source_color changed "
                    f"({expected} -> {actual})"
                )
                continue

            key = (seed, lightness, mode, role)
            if delta <= TOLERANCE:
                assert key not in KNOWN_DIVERGENCES, (
                    f"{seed} / {lightness} / {mode} / {role} now matches matugen "
                    f"({expected} -> {actual}); remove it from KNOWN_DIVERGENCES"
                )
                continue

            recorded = KNOWN_DIVERGENCES.get(key)
            assert recorded is not None, (
                f"unrecorded delta on {seed} / {lightness} / {mode} / {role}: "
                f"matugen={expected}, native={actual} (delta {delta} > {TOLERANCE}). "
                "Record the exact values in KNOWN_DIVERGENCES if intended."
            )
            assert recorded == (expected, actual), (
                f"recorded delta changed for {seed} / {lightness} / {mode} / {role}: "
                f"recorded {recorded}, actual {(expected, actual)}; re-record it."
            )
            severity = "material" if delta > MATERIAL else "small"
            pytest.xfail(
                f"known {severity} delta ({seed} / {lightness} / {mode} / {role}): "
                f"matugen={expected}, native={actual}, delta {delta}"
            )


def test_palettes_are_lightness_independent() -> None:
    """Palettes stay byte-identical to matugen at every lightness argument."""
    seed = SEEDS[0]
    for lightness in LIGHTNESS_VALUES:
        matugen = _matugen_payload(seed=seed, lightness=lightness)
        native = _native_payload(seed, lightness)
        for palette, tones in matugen["palettes"].items():
            for tone, node in tones.items():
                assert native["modes"]["dark"]["palettes"][palette][tone] == node["color"], (
                    f"palette {palette}[{tone}] drifted at lightness {lightness}"
                )


def test_report_delta_table() -> None:
    """Print the recorded corpus summary (run with ``-s`` to see it)."""
    assert _ROWS, "no oracle rows were produced"
    exact = sum(1 for row in _ROWS if row[4] == 0)
    within = sum(1 for row in _ROWS if row[4] <= TOLERANCE)
    worst = max(row[4] for row in _ROWS)
    print(
        f"\n{exact}/{len(_ROWS)} role comparisons exact; "
        f"{within}/{len(_ROWS)} within ±{TOLERANCE}; worst delta {worst}; "
        f"material threshold >{MATERIAL}"
    )
    print(f"seeds: {', '.join(SEEDS)}")
    print(f"lightness values: {', '.join(str(value) for value in LIGHTNESS_VALUES)}")
    for seed in SEEDS:
        for lightness in LIGHTNESS_VALUES:
            rows = [row for row in _ROWS if row[0] == seed and row[1] == lightness]
            print(
                f"{seed:9s} {lightness:5.1f}  comparisons={len(rows):4d}  "
                f"worst={max((row[4] for row in rows), default=0)}"
            )
