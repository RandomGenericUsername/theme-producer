from __future__ import annotations

import math
from pathlib import Path

import pytest
from PIL import Image

from theme_producer.adapters.image_metrics import PillowImageMetrics
from theme_producer.domain.engines import ThemeRequest
from theme_producer.domain.enums import SourceKind
from theme_producer.domain.exceptions import InvalidImageMetricsError
from theme_producer.domain.scheme_policy import ImageMetrics
from theme_producer.ports.image_metrics import ImageMetricsPort

REC709_RED = 0.2126
REC709_GREEN = 0.7152
REC709_BLUE = 0.0722


def _solid(path: Path, rgb: tuple[int, int, int], size: tuple[int, int] = (32, 32)) -> Path:
    Image.new("RGB", size, rgb).save(path)
    return path


def _quadrants(path: Path, colors: tuple[tuple[int, int, int], ...]) -> Path:
    """A 256x256 image split into equal vertical bands (no resize smoothing)."""
    image = Image.new("RGB", (256, 256))
    band = 256 // len(colors)
    for index, rgb in enumerate(colors):
        for x in range(index * band, (index + 1) * band):
            for y in range(256):
                image.putpixel((x, y), rgb)
    image.save(path)
    return path


def _measure_image(path: Path) -> ImageMetrics:
    return PillowImageMetrics().measure(ThemeRequest(SourceKind.IMAGE, image_path=path))


def _measure_color(value: str) -> ImageMetrics:
    return PillowImageMetrics().measure(ThemeRequest(SourceKind.COLOR, color=value))


def _assert_unit(metrics: ImageMetrics) -> None:
    for name in ("saturation", "colorfulness", "lightness", "contrast", "hue_diversity"):
        value = getattr(metrics, name)
        assert isinstance(value, float)
        assert math.isfinite(value)
        assert 0.0 <= value <= 1.0, (name, value)


def test_adapter_implements_the_port() -> None:
    assert isinstance(PillowImageMetrics(), ImageMetricsPort)


def test_white_and_black_are_the_luminance_extremes(tmp_path: Path) -> None:
    white = _measure_image(_solid(tmp_path / "white.png", (255, 255, 255)))
    black = _measure_image(_solid(tmp_path / "black.png", (0, 0, 0)))

    _assert_unit(white)
    _assert_unit(black)
    assert white.lightness == pytest.approx(1.0)
    assert white.saturation == 0.0
    assert white.colorfulness == 0.0
    assert white.contrast == 0.0
    assert white.hue_diversity == 0.0
    assert black.lightness == pytest.approx(0.0)
    assert black.saturation == 0.0
    assert black.colorfulness == 0.0
    assert black.contrast == 0.0
    assert black.hue_diversity == 0.0


@pytest.mark.parametrize(
    ("rgb", "expected_lightness", "expected_colorfulness"),
    [
        # Hasler-Süsstrunk on a solid color has no variance, only the mean term:
        # 0.3 * hypot(|rg|, |yb|) / 255.
        ((255, 0, 0), REC709_RED, 0.3 * math.hypot(255.0, 127.5) / 255.0),
        ((0, 255, 0), REC709_GREEN, 0.3 * math.hypot(255.0, 127.5) / 255.0),
        ((0, 0, 255), REC709_BLUE, 0.3 * math.hypot(0.0, 255.0) / 255.0),
    ],
)
def test_primary_solid_colors_follow_the_formulas(
    tmp_path: Path,
    rgb: tuple[int, int, int],
    expected_lightness: float,
    expected_colorfulness: float,
) -> None:
    metrics = _measure_image(_solid(tmp_path / "primary.png", rgb))

    _assert_unit(metrics)
    assert metrics.saturation == pytest.approx(1.0)
    assert metrics.lightness == pytest.approx(expected_lightness)
    assert metrics.colorfulness == pytest.approx(expected_colorfulness)
    assert metrics.contrast == pytest.approx(0.0)
    assert metrics.hue_diversity == pytest.approx(0.0)


def test_muted_gray_has_no_chroma(tmp_path: Path) -> None:
    metrics = _measure_image(_solid(tmp_path / "gray.png", (128, 128, 128)))

    _assert_unit(metrics)
    assert metrics.saturation == 0.0
    assert metrics.colorfulness == 0.0
    assert metrics.contrast == 0.0
    assert metrics.hue_diversity == 0.0
    # sRGB byte 128 linearizes to ~0.216, not 0.5.
    assert metrics.lightness == pytest.approx(0.2159, abs=1e-3)


def test_contrast_is_normalized_by_the_maximum_population_stddev(tmp_path: Path) -> None:
    # Half black, half white: mean L = 0.5, population std-dev = 0.5 -> 1.0.
    image = Image.new("RGB", (256, 256), (0, 0, 0))
    for x in range(128, 256):
        for y in range(256):
            image.putpixel((x, y), (255, 255, 255))
    path = tmp_path / "half.png"
    image.save(path)

    metrics = _measure_image(path)

    _assert_unit(metrics)
    assert metrics.lightness == pytest.approx(0.5)
    assert metrics.contrast == pytest.approx(1.0)


def test_colorful_quadrants_are_saturated_contrasty_and_hue_diverse(tmp_path: Path) -> None:
    metrics = _measure_image(
        _quadrants(tmp_path / "rgbw.png", ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)))
    )

    _assert_unit(metrics)
    assert metrics.saturation == pytest.approx(0.75)
    assert metrics.colorfulness > 0.5
    assert metrics.contrast > 0.5
    # Three saturated hues at 120 degrees apart plus a zero-weight white band:
    # the weighted mean vector cancels out, so the variance is ~1.
    assert metrics.hue_diversity > 0.99
    assert metrics.lightness == pytest.approx((REC709_RED + REC709_GREEN + REC709_BLUE + 1.0) / 4.0)


def test_two_opposite_hues_have_maximum_hue_diversity(tmp_path: Path) -> None:
    metrics = _measure_image(_quadrants(tmp_path / "red-cyan.png", ((255, 0, 0), (0, 255, 255))))

    _assert_unit(metrics)
    assert metrics.hue_diversity == pytest.approx(1.0)


def test_color_source_derives_saturation_and_lightness_only() -> None:
    red = _measure_color("#ff0000")

    _assert_unit(red)
    assert red.saturation == pytest.approx(1.0)
    assert red.lightness == pytest.approx(REC709_RED)
    assert red.colorfulness == 0.0
    assert red.contrast == 0.0
    assert red.hue_diversity == 0.0

    gray = _measure_color("#808080")
    assert gray.saturation == 0.0
    assert gray.lightness == pytest.approx(0.2159, abs=1e-3)


def test_color_source_accepts_uppercase_hex() -> None:
    assert _measure_color("#FF0000") == _measure_color("#ff0000")


def test_invalid_color_source_raises_the_metrics_error() -> None:
    with pytest.raises(InvalidImageMetricsError, match="invalid seed color"):
        _measure_color("not-a-color")


def test_json_source_is_rejected_with_the_typed_error(tmp_path: Path) -> None:
    path = tmp_path / "theme.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(InvalidImageMetricsError, match="json request has no measurable source"):
        PillowImageMetrics().measure(ThemeRequest(SourceKind.JSON, json_path=path))


def test_undecodable_image_raises_the_metrics_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.png"
    path.write_bytes(b"not an image")

    with pytest.raises(InvalidImageMetricsError, match="cannot decode image"):
        _measure_image(path)


def test_measurement_is_deterministic_and_size_independent(tmp_path: Path) -> None:
    small = _solid(tmp_path / "small.png", (240, 120, 40), (16, 16))
    large = _solid(tmp_path / "large.png", (240, 120, 40), (512, 512))

    adapter = PillowImageMetrics()
    first = adapter.measure(ThemeRequest(SourceKind.IMAGE, image_path=small))
    second = adapter.measure(ThemeRequest(SourceKind.IMAGE, image_path=small))
    resized_source = adapter.measure(ThemeRequest(SourceKind.IMAGE, image_path=large))

    assert first == second == resized_source
