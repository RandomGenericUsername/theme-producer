"""Recorded corpus table for ``scheme-smart`` calibration (REQ-021).

The seven real wallpapers are host state, not repo fixtures: the hermetic gate
empties ``HOME`` and this suite skips with the exact reason. When the corpus is
present it pins both the measured metrics and the variant each built-in profile
chooses, so a threshold/normalizer drift fails loudly instead of silently
changing user output.

Run ``pytest -s tests/contract/test_scheme_policy_corpus.py`` to print the table.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from theme_producer.adapters.image_metrics import PillowImageMetrics
from theme_producer.adapters.scheme_policy_catalog_loader import YamlSchemePolicyCatalogLoader
from theme_producer.domain.engines import ThemeRequest
from theme_producer.domain.scheme_policy_resolver import SchemePolicyResolver

# Captured at import time, before tests/conftest.py replaces HOME per test.
_HOST_HOME = Path(os.path.expanduser("~"))
WALLPAPER_DIR = _HOST_HOME / ".local" / "share" / "dotfiles" / "wallpapers"

#: name -> (saturation, colorfulness, lightness, contrast, hue_diversity)
RECORDED_METRICS: dict[str, tuple[float, float, float, float, float]] = {
    "zenitsu-agatsuma-3840x2160-26517.png": (0.097, 0.145, 0.014, 0.140, 0.036),
    "windows-95-dark-3840x2160-27097.jpg": (0.191, 0.143, 0.178, 0.357, 0.096),
    "gargantua-black-3840x2160-9621.jpg": (0.220, 0.078, 0.063, 0.305, 0.603),
    "japan-artistic-3840x2160-25406.jpg": (0.260, 0.233, 0.346, 0.669, 0.583),
    "astronaut-purple-3840x2160-22432.jpg": (0.550, 0.225, 0.148, 0.353, 0.172),
    "yasuke-dark-7680x4320-21997.jpg": (0.416, 0.136, 0.044, 0.319, 0.884),
    "aurora.jpg": (0.594, 0.292, 0.148, 0.351, 0.674),
}

PROFILES = ("balanced", "vivid", "muted", "source-faithful")

#: name -> profile -> chosen variant
RECORDED_PICKS: dict[str, dict[str, str]] = {
    "zenitsu-agatsuma-3840x2160-26517.png": {
        "balanced": "scheme-neutral",
        "vivid": "scheme-neutral",
        "muted": "scheme-neutral",
        "source-faithful": "scheme-content",
    },
    "windows-95-dark-3840x2160-27097.jpg": {
        "balanced": "scheme-tonal-spot",
        "vivid": "scheme-vibrant",
        "muted": "scheme-neutral",
        "source-faithful": "scheme-content",
    },
    "gargantua-black-3840x2160-9621.jpg": {
        "balanced": "scheme-monochrome",
        "vivid": "scheme-neutral",
        "muted": "scheme-neutral",
        "source-faithful": "scheme-content",
    },
    "japan-artistic-3840x2160-25406.jpg": {
        "balanced": "scheme-tonal-spot",
        "vivid": "scheme-vibrant",
        "muted": "scheme-neutral",
        "source-faithful": "scheme-fidelity",
    },
    "astronaut-purple-3840x2160-22432.jpg": {
        "balanced": "scheme-vibrant",
        "vivid": "scheme-vibrant",
        "muted": "scheme-tonal-spot",
        "source-faithful": "scheme-content",
    },
    "yasuke-dark-7680x4320-21997.jpg": {
        "balanced": "scheme-expressive",
        "vivid": "scheme-vibrant",
        "muted": "scheme-expressive",
        "source-faithful": "scheme-content",
    },
    "aurora.jpg": {
        "balanced": "scheme-vibrant",
        "vivid": "scheme-vibrant",
        "muted": "scheme-tonal-spot",
        "source-faithful": "scheme-content",
    },
}

CORPUS = tuple(
    WALLPAPER_DIR / name for name in RECORDED_METRICS if (WALLPAPER_DIR / name).is_file()
)
_SKIP_REASON = (
    "real wallpapers are absent (expected seven files in "
    f"{WALLPAPER_DIR}); the hermetic gate empties HOME by design"
)
pytestmark = pytest.mark.skipif(len(CORPUS) != len(RECORDED_METRICS), reason=_SKIP_REASON)

_ROWS: list[tuple[str, tuple[float, ...], dict[str, str]]] = []


@pytest.fixture(scope="module", autouse=True)
def _measure_corpus() -> None:
    _ROWS.clear()
    catalog = YamlSchemePolicyCatalogLoader().load()
    adapter = PillowImageMetrics()
    for name in RECORDED_METRICS:
        path = WALLPAPER_DIR / name
        metrics = adapter.measure(ThemeRequest(source_kind="image", image_path=path))
        measured = (
            metrics.saturation,
            metrics.colorfulness,
            metrics.lightness,
            metrics.contrast,
            metrics.hue_diversity,
        )
        picks = {
            profile: SchemePolicyResolver.resolve(catalog.select(profile), metrics).value
            for profile in PROFILES
        }
        _ROWS.append((name, measured, picks))


def test_corpus_metrics_match_the_recorded_table() -> None:
    assert len(_ROWS) == len(RECORDED_METRICS)
    for name, measured, _picks in _ROWS:
        expected = RECORDED_METRICS[name]
        for field, value, recorded in zip(
            ("saturation", "colorfulness", "lightness", "contrast", "hue_diversity"),
            measured,
            expected,
            strict=True,
        ):
            assert value == pytest.approx(recorded, abs=1e-3), (name, field, value, recorded)


def test_corpus_picks_match_the_recorded_table() -> None:
    for name, _measured, picks in _ROWS:
        assert picks == RECORDED_PICKS[name], name


def test_profiles_produce_more_than_one_variant_across_the_corpus() -> None:
    for profile in PROFILES:
        variants = {picks[profile] for _name, _measured, picks in _ROWS}
        assert len(variants) > 1, (profile, variants)


def test_report_corpus_table() -> None:
    """Print the recorded table (run with ``-s``)."""
    print(
        f"{'wallpaper':44s} {'sat':>5} {'color':>6} {'light':>6} {'contr':>6} {'hue':>6} "
        + " ".join(f"{profile:>15}" for profile in PROFILES)
    )
    print("-" * 120)
    for name, measured, picks in _ROWS:
        print(
            f"{name:44s} "
            + " ".join(f"{value:5.3f}" for value in measured)
            + " | "
            + " ".join(f"{picks[profile]:>15}" for profile in PROFILES)
        )
