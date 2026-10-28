from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from theme_producer.domain import (
    TONE_ORDER,
    Color,
    GeneratorMetadata,
    MaterialRole,
    Mode,
    ModeName,
    PaletteName,
    Source,
    SourceKind,
    Theme,
    ThemeValidationError,
    TonalPalette,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"


def _color(index: int) -> Color:
    return Color.from_rgb(index % 256, (index * 7) % 256, (index * 13) % 256)


def _palette(name: PaletteName, offset: int) -> TonalPalette:
    return TonalPalette(
        name=name,
        tones={tone: _color(tone + offset) for tone in TONE_ORDER},
    )


def build_mode(mode: ModeName) -> Mode:
    mode_offset = 0 if mode is ModeName.DARK else 1
    palettes = {
        name: _palette(name, index * 100 + mode_offset) for index, name in enumerate(PaletteName)
    }
    roles = {role: _color(index * 3 + mode_offset) for index, role in enumerate(MaterialRole)}
    return Mode(mode=mode, roles=roles, palettes=palettes)


def build_theme() -> Theme:
    return Theme(
        source=Source(kind=SourceKind.IMAGE, path="/wallpapers/seed.png", hash="abc123"),
        scheme="scheme-tonal-spot",
        contrast=0.0,
        dark=build_mode(ModeName.DARK),
        light=build_mode(ModeName.LIGHT),
        generator=GeneratorMetadata(engine="matugen", engine_version="4.2.0", schema_version="1"),
    )


def load_fixture() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text()))


def test_golden_fixture_round_trips_exactly() -> None:
    raw = FIXTURE.read_text()
    payload = json.loads(raw)

    theme = Theme.from_dict(payload)

    assert theme.to_dict() == payload
    assert json.dumps(theme.to_dict(), indent=2) + "\n" == raw


def test_fixture_theme_has_expected_50_roles_and_six_by_18_palettes() -> None:
    theme = load_fixture()

    for mode in (theme.dark, theme.light):
        assert len(mode.roles) == 50
        assert set(mode.roles) == set(MaterialRole)
        assert len(mode.palettes) == 6
        assert set(mode.palettes) == set(PaletteName)
        for palette in mode.palettes.values():
            assert len(palette.tones) == 18
            assert set(palette.tones) == set(TONE_ORDER)


def test_programmatic_theme_has_expected_counts() -> None:
    theme = build_theme()

    assert len(theme.dark.roles) == 50
    assert len(theme.light.roles) == 50
    assert len(theme.dark.palettes) == 6
    assert len(theme.light.palettes) == 6
    assert all(len(palette.tones) == 18 for palette in theme.dark.palettes.values())
    assert theme.to_dict()["schema_version"] == "1"


def test_color_derives_rgb_and_normalizes_hex_case() -> None:
    color = Color("#ABCDEF")

    assert color.rgb == (0xAB, 0xCD, 0xEF)
    assert color.hex == "#abcdef"
    assert color.to_dict() == "#abcdef"


def test_color_clamps_and_rounds_rgb_then_resyncs_hex() -> None:
    color = Color("#000000", (300, -5, 12.6))

    assert color.rgb == (255, 0, 13)
    assert color.hex == "#ff000d"


@pytest.mark.parametrize(
    "bad_hex",
    ["#12345", "#1234567", "123456", "#gggggg", "#12345g", "", None],
)
def test_color_rejects_invalid_hex(bad_hex: object) -> None:
    with pytest.raises(ThemeValidationError, match="Color hex must match"):
        Color(bad_hex)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_rgb", [(1, 2), (1, 2, 3, 4), (1, 2, math.nan), (True, 0, 0)])
def test_color_rejects_invalid_rgb(bad_rgb: object) -> None:
    with pytest.raises(ThemeValidationError):
        Color("#000000", bad_rgb)  # type: ignore[arg-type]


def test_source_accepts_string_or_enum_kind() -> None:
    assert Source(kind="image", path="a.png").kind is SourceKind.IMAGE
    assert Source(kind=SourceKind.COLOR).to_dict() == {
        "kind": "color",
        "path": None,
        "hash": None,
    }


def test_source_rejects_unknown_kind() -> None:
    with pytest.raises(ThemeValidationError, match="source kind"):
        Source(kind="wallpaper")


def test_generator_metadata_rejects_empty_fields() -> None:
    with pytest.raises(ThemeValidationError, match="generator engine"):
        GeneratorMetadata(engine="", engine_version="4.2.0", schema_version="1")


def test_palette_rejects_missing_tone() -> None:
    palette = _palette(PaletteName.PRIMARY, 0)
    tones = dict(palette.tones)
    tones.pop(100)

    with pytest.raises(ThemeValidationError, match="missing=\\[100\\]"):
        TonalPalette(name=PaletteName.PRIMARY, tones=tones)


def test_palette_rejects_extra_tone() -> None:
    palette = _palette(PaletteName.PRIMARY, 0)
    tones = {**palette.tones, 42: _color(1)}

    with pytest.raises(ThemeValidationError, match="extra=\\[42\\]"):
        TonalPalette(name=PaletteName.PRIMARY, tones=tones)


def test_palette_rejects_non_integer_tone() -> None:
    palette = _palette(PaletteName.PRIMARY, 0)
    tones = {**palette.tones, "50": _color(1)}

    with pytest.raises(ThemeValidationError, match="tone keys must be ints"):
        TonalPalette(name=PaletteName.PRIMARY, tones=tones)  # type: ignore[dict-item]


def test_mode_rejects_missing_role() -> None:
    theme = build_theme()
    roles = dict(theme.dark.roles)
    roles.pop(MaterialRole.SURFACE)

    with pytest.raises(ThemeValidationError, match="missing Material roles.*surface"):
        Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)


def test_mode_rejects_unknown_role() -> None:
    theme = build_theme()
    roles = {**theme.dark.roles, "not_a_role": _color(1)}

    with pytest.raises(ThemeValidationError, match="unknown Material role 'not_a_role'"):
        Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)  # type: ignore[dict-item]


def test_mode_rejects_wrong_palette_count() -> None:
    theme = build_theme()
    palettes = dict(theme.dark.palettes)
    palettes.pop(PaletteName.ERROR)

    with pytest.raises(ThemeValidationError, match="exactly 6 palettes"):
        Mode(mode=ModeName.DARK, roles=theme.dark.roles, palettes=palettes)


def test_mode_rejects_mismatched_palette_name() -> None:
    theme = build_theme()
    palettes = dict(theme.dark.palettes)
    palettes[PaletteName.ERROR] = _palette(PaletteName.PRIMARY, 0)

    with pytest.raises(ThemeValidationError, match="mismatched TonalPalette name"):
        Mode(mode=ModeName.DARK, roles=theme.dark.roles, palettes=palettes)


@pytest.mark.parametrize(
    "contrast",
    [-1.01, 1.01, math.nan, math.inf, -math.inf, "0.5", True],
)
def test_theme_rejects_invalid_contrast(contrast: object) -> None:
    with pytest.raises(ThemeValidationError, match="contrast"):
        Theme(
            source=Source(kind="image", path="a.png"),
            scheme="scheme-tonal-spot",
            contrast=contrast,  # type: ignore[arg-type]
            dark=build_mode(ModeName.DARK),
            light=build_mode(ModeName.LIGHT),
            generator=GeneratorMetadata("matugen", "4.2.0", "1"),
        )


def test_theme_accepts_boundary_contrast() -> None:
    theme = build_theme()

    assert (
        Theme(
            source=theme.source,
            scheme=theme.scheme,
            contrast=-1,
            dark=theme.dark,
            light=theme.light,
            generator=theme.generator,
        ).contrast
        == -1.0
    )
    assert (
        Theme(
            source=theme.source,
            scheme=theme.scheme,
            contrast=1,
            dark=theme.dark,
            light=theme.light,
            generator=theme.generator,
        ).contrast
        == 1.0
    )


def test_theme_rejects_empty_scheme() -> None:
    with pytest.raises(ThemeValidationError, match="scheme must be a non-empty string"):
        Theme(
            source=Source(kind="color"),
            scheme="  ",
            contrast=0.0,
            dark=build_mode(ModeName.DARK),
            light=build_mode(ModeName.LIGHT),
            generator=GeneratorMetadata("matugen", "4.2.0", "1"),
        )


def test_theme_rejects_wrong_mode_direction() -> None:
    with pytest.raises(ThemeValidationError, match="dark must be a Mode"):
        Theme(
            source=Source(kind="color"),
            scheme="scheme-tonal-spot",
            contrast=0.0,
            dark=build_mode(ModeName.LIGHT),
            light=build_mode(ModeName.LIGHT),
            generator=GeneratorMetadata("matugen", "4.2.0", "1"),
        )


def test_from_dict_rejects_unknown_schema_version() -> None:
    payload = json.loads(FIXTURE.read_text())
    payload["schema_version"] = "2"

    with pytest.raises(ThemeValidationError, match="unsupported theme schema_version"):
        Theme.from_dict(payload)
