from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from theme_producer.domain.enums import ModeName
from theme_producer.domain.generation import (
    InvalidSmartThresholdError,
    SmartModeError,
    UnknownModeError,
)
from theme_producer.domain.smart_mode import (
    image_mean_luminance,
    mean_relative_luminance,
    parse_projection_mode,
    relative_luminance_from_hex,
    resolve_projection_mode,
    resolve_smart_mode,
    validate_threshold,
)


def _solid(path: Path, rgb: tuple[int, int, int], size: tuple[int, int] = (8, 8)) -> Path:
    Image.new("RGB", size, rgb).save(path)
    return path


def test_white_black_and_mid_gray_luminance(tmp_path: Path) -> None:
    white = _solid(tmp_path / "white.png", (255, 255, 255))
    black = _solid(tmp_path / "black.png", (0, 0, 0))
    # sRGB byte 188 linearizes to ~0.502; #808080 would be ~0.216.
    mid_gray = _solid(tmp_path / "mid-gray.png", (188, 188, 188))

    assert image_mean_luminance(white) == pytest.approx(1.0, abs=0.01)
    assert image_mean_luminance(black) == pytest.approx(0.0, abs=0.01)
    assert image_mean_luminance(mid_gray) == pytest.approx(0.5, abs=0.01)


def test_mean_luminance_accepts_an_open_image() -> None:
    assert mean_relative_luminance(Image.new("RGB", (4, 4), (255, 255, 255))) == pytest.approx(
        1.0, abs=0.01
    )


@pytest.mark.parametrize(
    ("rgb", "expected"),
    [
        ((240, 240, 240), ModeName.LIGHT),
        ((10, 10, 10), ModeName.DARK),
    ],
)
def test_bright_and_dark_images_resolve_at_default_threshold(
    tmp_path: Path, rgb: tuple[int, int, int], expected: ModeName
) -> None:
    image = _solid(tmp_path / "wall.png", rgb)

    assert resolve_projection_mode("smart", image_path=image, threshold=0.5) is expected


def test_threshold_changes_the_decision(tmp_path: Path) -> None:
    # sRGB 203 linearizes to ~0.596, so the mean is ~0.6.
    image = _solid(tmp_path / "mean-06.png", (203, 203, 203))
    luminance = image_mean_luminance(image)
    assert luminance == pytest.approx(0.6, abs=0.01)

    assert resolve_smart_mode(luminance, 0.5) is ModeName.LIGHT
    assert resolve_smart_mode(luminance, 0.8) is ModeName.DARK


def test_color_source_uses_the_seed_luminance() -> None:
    assert relative_luminance_from_hex("#ffffff") == pytest.approx(1.0, abs=0.01)
    assert relative_luminance_from_hex("#000000") == pytest.approx(0.0, abs=0.01)
    assert resolve_projection_mode("smart", seed_color="#ffffff", threshold=0.5) is ModeName.LIGHT
    assert resolve_projection_mode("smart", seed_color="#000000", threshold=0.5) is ModeName.DARK


def test_smart_requires_a_source() -> None:
    with pytest.raises(SmartModeError, match="requires an image or seed color"):
        resolve_projection_mode("smart")


def test_parse_projection_mode_accepts_case_and_rejects_unknown() -> None:
    assert parse_projection_mode(" SMART ") == "smart"
    with pytest.raises(UnknownModeError, match="dark, light, smart"):
        parse_projection_mode("sepia")


@pytest.mark.parametrize("value", [0, 0.5, "0.25", 1, 1.0])
def test_valid_thresholds(value: object) -> None:
    assert 0.0 <= validate_threshold(value) <= 1.0


@pytest.mark.parametrize("value", [-0.1, 1.1, "nan", "inf", True, "half", None])
def test_invalid_thresholds_are_typed(value: object) -> None:
    with pytest.raises(InvalidSmartThresholdError, match=r"\[0, 1\]"):
        validate_threshold(value)


def test_undecodable_image_is_a_typed_error(tmp_path: Path) -> None:
    bogus = tmp_path / "not-an-image.png"
    bogus.write_bytes(b"not an image")

    with pytest.raises(SmartModeError, match="cannot decode image"):
        image_mean_luminance(bogus)
