"""Oracle corpus: native source-color parity with matugen on real wallpapers.

matugen 4.2.0 is GPL-2.0-or-later and is used ONLY as a black-box oracle here:
the test runs its binary (or the pinned container image) and compares the dark
mode's ``source_color`` and ``primary`` with ``tpr-native`` on the same image,
scheme, contrast, fallback, and preference.

Both engines downscale to 112x112 and rank four candidates with the
MIT/Apache-2.0 ``material-colors`` crate. The *selection* rules were derived
from this corpus (see ``native/src/main.rs``); the *candidate lists* still
diverge on some images because matugen vendors its own fork of
``material-colors``. Those pairs are pinned in ``KNOWN_DIVERGENCES`` with their
exact values and reported as xfails, never silently ignored: any new divergence
fails, and any change to a pinned pair fails until the table is re-recorded.

The suite skips with a clear reason when the host wallpapers are absent (the
hermetic gate empties ``HOME``) or when neither engine is reachable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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
FALLBACK = "#123456"

#: matugen 4.2.0's ranked-candidate pick list: a plain run needs an explicit
#: index in a non-interactive process, so ``None`` means ``--source-color-index 0``.
PREFERENCES: tuple[str | None, ...] = (
    None,
    "darkness",
    "lightness",
    "saturation",
    "less-saturation",
    "value",
    "closest-to-fallback",
)

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

#: A pair may differ by at most this many units per channel and still count as
#: rounding. Anything larger is recorded below.
TOLERANCE = 1
#: Beyond this the two engines picked genuinely different colors (a candidate
#: set difference, not rounding). Reported explicitly in the xfail reason.
MATERIAL = 16

#: Recorded divergences: (wallpaper, preference) -> (matugen source,
#: native source, matugen primary, native primary). Every entry is a known
#: candidate-extraction difference between ``material-colors`` 0.4.2 and
#: matugen's vendored fork; the exact values are asserted so a regression or an
#: improvement is visible instead of drifting.
KNOWN_DIVERGENCES: dict[tuple[str, str], tuple[str, str, str, str]] = {
    ("zenitsu-agatsuma-3840x2160-26517.png", "default"): (
        "#f9c711",
        "#f94e06",
        "#e3c36c",
        "#ffb59e",
    ),
    ("zenitsu-agatsuma-3840x2160-26517.png", "darkness"): (
        "#9a5110",
        "#f94e06",
        "#ffb784",
        "#ffb59e",
    ),
    ("zenitsu-agatsuma-3840x2160-26517.png", "less-saturation"): (
        "#9a5110",
        "#dc9215",
        "#ffb784",
        "#f6bc70",
    ),
    ("zenitsu-agatsuma-3840x2160-26517.png", "value"): (
        "#9a5110",
        "#dc9215",
        "#ffb784",
        "#f6bc70",
    ),
    ("zenitsu-agatsuma-3840x2160-26517.png", "closest-to-fallback"): (
        "#9a5110",
        "#dc9215",
        "#ffb784",
        "#f6bc70",
    ),
    ("windows-95-dark-3840x2160-27097.jpg", "lightness"): (
        "#7ec7f2",
        "#5799c6",
        "#90cef4",
        "#95cdf7",
    ),
    ("gargantua-black-3840x2160-9621.jpg", "default"): (
        "#0f1318",
        "#1b1d21",
        "#9fcafc",
        "#a6c8ff",
    ),
    ("gargantua-black-3840x2160-9621.jpg", "darkness"): (
        "#0f1318",
        "#1b1d21",
        "#9fcafc",
        "#a6c8ff",
    ),
    ("gargantua-black-3840x2160-9621.jpg", "value"): (
        "#0f1318",
        "#1b1d21",
        "#9fcafc",
        "#a6c8ff",
    ),
    ("gargantua-black-3840x2160-9621.jpg", "closest-to-fallback"): (
        "#0f1318",
        "#1b1d21",
        "#9fcafc",
        "#a6c8ff",
    ),
    ("japan-artistic-3840x2160-25406.jpg", "darkness"): (
        "#0c131c",
        "#0c1119",
        "#a2c9fd",
        "#a6c8ff",
    ),
    ("japan-artistic-3840x2160-25406.jpg", "less-saturation"): (
        "#14141c",
        "#0c1119",
        "#c0c1ff",
        "#a6c8ff",
    ),
    ("japan-artistic-3840x2160-25406.jpg", "value"): (
        "#0c131c",
        "#0c1119",
        "#a2c9fd",
        "#a6c8ff",
    ),
    ("japan-artistic-3840x2160-25406.jpg", "closest-to-fallback"): (
        "#0c131c",
        "#0c1119",
        "#a2c9fd",
        "#a6c8ff",
    ),
    ("yasuke-dark-7680x4320-21997.jpg", "lightness"): (
        "#3d332b",
        "#b80419",
        "#ffb877",
        "#ffb3ad",
    ),
}

_ROWS: list[tuple[str, str, str, str, str, str, int, int]] = []


def _corpus() -> list[Path]:
    files = [WALLPAPER_DIR / name for name in WALLPAPERS if (WALLPAPER_DIR / name).is_file()]
    files.extend(sorted(_HOST_HOME.glob(CACHE_GLOB))[-1:])
    return files


CORPUS = _corpus()


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


NATIVE = _native_binary()
MATUGEN = _matugen_binary()
HAS_MATUGEN_IMAGE = MATUGEN_IMAGE in _podman_images()

_SKIP_REASONS = []
if not CORPUS:
    _SKIP_REASONS.append(
        "real wallpapers are absent (expected seven files in "
        f"{WALLPAPER_DIR}); the hermetic gate empties HOME by design"
    )
if NATIVE is None:
    _SKIP_REASONS.append(
        "tpr-native is missing; run `cd native && cargo build --release --locked` "
        "and add native/target/release to PATH"
    )
if MATUGEN is None and not HAS_MATUGEN_IMAGE:
    _SKIP_REASONS.append(
        "matugen is missing; install matugen 4.2.0 on PATH, or build/load "
        f"the pinned `{MATUGEN_IMAGE}` image (make image)"
    )

pytestmark = pytest.mark.skipif(
    bool(_SKIP_REASONS), reason="oracle parity skipped: " + "; ".join(_SKIP_REASONS)
)


def _max_delta(left: str, right: str) -> int:
    return max(abs(int(left[i : i + 2], 16) - int(right[i : i + 2], 16)) for i in (1, 3, 5))


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


def _matugen_payload(
    image: Path, prefer: str | None, scratch: Path
) -> dict[str, Any]:
    config = scratch / "matugen.toml"
    config.write_text("[config]\n\n[templates]\n", encoding="utf-8")
    selector = ["--source-color-index", "0"] if prefer is None else ["--prefer", prefer]
    fallback = [] if prefer is None else ["--fallback-color", FALLBACK]
    if MATUGEN is not None:
        argv = [
            MATUGEN,
            "image",
            str(image),
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
            *selector,
            *fallback,
        ]
    else:
        podman = shutil.which("podman") or "podman"
        argv = [
            podman,
            "run",
            "--rm",
            "--entrypoint",
            "matugen",
            "-v",
            f"{image}:/wallpaper:ro",
            "-v",
            f"{config}:/matugen.toml:ro",
            MATUGEN_IMAGE,
            "image",
            "/wallpaper",
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
            "/matugen.toml",
            "--quiet",
            *selector,
            *fallback,
        ]
    return json.loads(_run(argv))


def _native_payload(image: Path, prefer: str | None) -> dict[str, Any]:
    assert NATIVE is not None
    selector = ["--source-color-index", "0"] if prefer is None else ["--prefer", prefer]
    argv = [
        NATIVE,
        "--image",
        str(image),
        "--scheme",
        SCHEME,
        "--contrast",
        CONTRAST,
        *selector,
        "--fallback-color",
        FALLBACK,
        "--json",
    ]
    return json.loads(_run(argv))


def _pair(
    wallpaper: Path, prefer: str | None, scratch: Path
) -> tuple[str, str, str, str]:
    matugen = _matugen_payload(wallpaper, prefer, scratch)
    native = _native_payload(wallpaper, prefer)
    roles = native["modes"]["dark"]["roles"]
    return (
        matugen["colors"]["source_color"]["dark"]["color"],
        roles["source_color"],
        matugen["colors"]["primary"]["dark"]["color"],
        roles["primary"],
    )


@pytest.mark.parametrize(
    ("wallpaper", "prefer"),
    [(wallpaper, prefer) for wallpaper in CORPUS for prefer in PREFERENCES],
    ids=lambda value: value.name if isinstance(value, Path) else value or "default",
)
def test_source_color_matches_matugen(
    wallpaper: Path, prefer: str | None, tmp_path: Path
) -> None:
    label = prefer or "default"
    matugen_source, native_source, matugen_primary, native_primary = _pair(
        wallpaper, prefer, tmp_path
    )
    source_delta = _max_delta(matugen_source, native_source)
    primary_delta = _max_delta(matugen_primary, native_primary)

    _ROWS.append(
        (
            wallpaper.name,
            label,
            matugen_source,
            native_source,
            matugen_primary,
            native_primary,
            source_delta,
            primary_delta,
        )
    )

    key = (wallpaper.name, label)
    if source_delta <= TOLERANCE and primary_delta <= TOLERANCE:
        assert key not in KNOWN_DIVERGENCES, (
            f"{wallpaper.name} / {label} now matches matugen "
            f"({matugen_source} -> {matugen_primary}); remove it from KNOWN_DIVERGENCES"
        )
        return

    recorded = KNOWN_DIVERGENCES.get(key)
    actual = (matugen_source, native_source, matugen_primary, native_primary)
    assert recorded is not None, (
        f"unrecorded divergence on {wallpaper.name} / {label}: "
        f"matugen source={matugen_source} primary={matugen_primary}, "
        f"native source={native_source} primary={native_primary} "
        f"(source delta {source_delta}, primary delta {primary_delta})"
    )
    assert actual == recorded, (
        f"recorded divergence changed for {wallpaper.name} / {label}: "
        f"recorded {recorded}, actual {actual}. Re-record KNOWN_DIVERGENCES if the "
        "new values are the intended behavior."
    )

    severity = "material" if max(source_delta, primary_delta) > MATERIAL else "small"
    pytest.xfail(
        f"known {severity} divergence ({wallpaper.name} / {label}): "
        f"matugen source={matugen_source} primary={matugen_primary}; "
        f"native source={native_source} primary={native_primary}; "
        f"deltas source={source_delta} primary={primary_delta}. "
        "Cause: matugen vendors its own material-colors fork, so the ranked "
        "candidate list differs before preference selection runs."
    )


def test_report_delta_table() -> None:
    """Print the recorded corpus table (run with ``-s`` to see it)."""
    assert _ROWS, "no oracle rows were produced"
    header = (
        f"{'wallpaper':40s} {'prefer':20s} {'matugen src':11s} {'native src':11s} "
        f"{'d(src)':>7s} {'matugen pri':11s} {'native pri':11s} {'d(pri)':>7s}"
    )
    print(header)
    print("-" * len(header))
    for row in _ROWS:
        print(
            f"{row[0]:40s} {row[1]:20s} {row[2]:11s} {row[3]:11s} {row[6]:7d} "
            f"{row[4]:11s} {row[5]:11s} {row[7]:7d}"
        )
    exact = sum(1 for row in _ROWS if row[6] == 0 and row[7] == 0)
    within = sum(1 for row in _ROWS if row[6] <= TOLERANCE and row[7] <= TOLERANCE)
    print(
        f"\n{exact}/{len(_ROWS)} pairs exact; {within}/{len(_ROWS)} within ±{TOLERANCE}; "
        f"material threshold >{MATERIAL}"
    )
