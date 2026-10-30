from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from theme_producer.adapters.on_backdrop import theme_with_on_backdrop
from theme_producer.domain.color_metrics import relative_luminance
from theme_producer.domain.enums import MaterialRole, SourceKind
from theme_producer.domain.models import Source, Theme

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def _image(path: Path, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Path:
    image = Image.new("RGB", (64, 96), bottom)
    for y in range(48):
        for x in range(64):
            image.putpixel((x, y), top)
    image.save(path)
    return path


def test_image_source_measures_and_selects_for_both_modes(tmp_path: Path) -> None:
    theme = load_theme()
    image = _image(tmp_path / "bright-band.png", (255, 255, 255), (0, 0, 0))

    applied = theme_with_on_backdrop(theme, image)

    for mode in (applied.dark, applied.light):
        assert mode.on_backdrop is not None
        assert relative_luminance(mode.on_backdrop) < 0.1


def test_color_source_keeps_the_on_surface_fallback(tmp_path: Path) -> None:
    theme = replace(load_theme(), source=Source(kind=SourceKind.COLOR, hash="deadbeef"))
    image = _image(tmp_path / "bright-band.png", (255, 255, 255), (0, 0, 0))

    applied = theme_with_on_backdrop(theme, image)

    assert applied.dark.on_backdrop == applied.dark.roles[MaterialRole.ON_SURFACE]
    assert applied.light.on_backdrop == applied.light.roles[MaterialRole.ON_SURFACE]


def test_json_source_keeps_the_on_surface_fallback(tmp_path: Path) -> None:
    theme = replace(load_theme(), source=Source(kind=SourceKind.JSON))
    image = _image(tmp_path / "bright-band.png", (255, 255, 255), (0, 0, 0))

    applied = theme_with_on_backdrop(theme, image)

    assert applied.dark.on_backdrop == applied.dark.roles[MaterialRole.ON_SURFACE]
    assert applied.light.on_backdrop == applied.light.roles[MaterialRole.ON_SURFACE]


def test_missing_or_undecodable_image_keeps_the_fallback(tmp_path: Path) -> None:
    theme = load_theme()
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")

    assert theme_with_on_backdrop(theme, None).dark.on_backdrop == theme.dark.on_backdrop
    assert theme_with_on_backdrop(theme, broken).dark.on_backdrop == theme.dark.on_backdrop


def test_same_image_is_engine_independent(tmp_path: Path) -> None:
    theme = load_theme()
    matugen = replace(
        theme,
        generator=replace(theme.generator, engine="matugen", engine_version="4.2.0"),
    )
    native = replace(
        theme,
        generator=replace(theme.generator, engine="native", engine_version="0.1.0"),
    )
    image = _image(tmp_path / "band.png", (240, 200, 120), (20, 20, 20))

    applied_matugen = theme_with_on_backdrop(matugen, image)
    applied_native = theme_with_on_backdrop(native, image)

    assert applied_matugen.dark.on_backdrop == applied_native.dark.on_backdrop
    assert applied_matugen.light.on_backdrop == applied_native.light.on_backdrop


@pytest.mark.parametrize("mode_name", ["dark", "light"])
def test_applied_role_round_trips_through_the_canonical_json(tmp_path: Path, mode_name: str) -> None:
    theme = load_theme()
    image = _image(tmp_path / "band.png", (255, 255, 255), (0, 0, 0))

    applied = theme_with_on_backdrop(theme, image)
    reloaded = Theme.from_dict(applied.to_dict())

    assert getattr(reloaded, mode_name).on_backdrop == getattr(applied, mode_name).on_backdrop
