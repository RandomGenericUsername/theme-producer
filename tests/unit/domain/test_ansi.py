from __future__ import annotations

import colorsys
import json
from dataclasses import replace
from pathlib import Path

import pytest

from theme_producer.domain.ansi import (
    ANSI_BRIGHT_LIGHTNESS,
    ANSI_COLOR_COUNT,
    ANSI_HUE_ANCHORS,
    ANSI_HUE_FAMILY_BOUND,
    ANSI_HUE_TINT_MAX,
    ANSI_HUE_TINT_STEP,
    ANSI_MIN_HUE_SEPARATION,
    ANSI_NORMAL_LIGHTNESS,
    ANSI_SATURATION_FALLBACK,
    ANSI_SATURATION_MAX,
    ANSI_SATURATION_MIN,
    ANSI_SLOT_ROLES,
    _tinted_hues,
    ansi_palette,
)
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"

#: 8-bit RGB rounding can move a stored hue by about a degree.
QUANTIZATION_TOLERANCE = 1.5


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def hls(color: Color) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*(channel / 255.0 for channel in color.rgb))


def hue_degrees(color: Color) -> float:
    return hls(color)[0] * 360.0


def circular_distance(first: float, second: float) -> float:
    return abs((second - first + 180.0) % 360.0 - 180.0)


def in_family(color: Color, anchor: float) -> bool:
    return (
        circular_distance(hue_degrees(color), anchor)
        <= ANSI_HUE_FAMILY_BOUND + QUANTIZATION_TOLERANCE
    )


def mutate_role(theme: Theme, role_name: str, hex_value: str) -> Theme:
    role = MaterialRole(role_name)
    roles = dict(theme.dark.roles)
    roles[role] = Color.from_hex(hex_value)
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def primary_hue_theme(hue: float, saturation: float = 0.80) -> Theme:
    red, green, blue = colorsys.hls_to_rgb(hue / 360.0, 0.50, saturation)
    primary = Color.from_rgb(red * 255.0, green * 255.0, blue * 255.0)
    return mutate_role(load_theme(), "primary", primary.hex)


def primary_hue(theme: Theme) -> float:
    return hue_degrees(theme.dark.roles[MaterialRole.PRIMARY])


def low_chroma_theme() -> Theme:
    """The fixture's near-achromatic primary with distinct low-chroma anchors.

    The canonical fixture's surface/on-surface-variant/outline-variant roles all
    happen to be ``#000000``; distinct anchor tones keep the 16-slot assertion
    about the ANSI recipe rather than about that fixture coincidence.
    """
    theme = load_theme()
    roles = dict(theme.dark.roles)
    roles[MaterialRole.SURFACE] = Color.from_hex("#17130f")
    roles[MaterialRole.ON_SURFACE_VARIANT] = Color.from_hex("#6f675e")
    roles[MaterialRole.OUTLINE_VARIANT] = Color.from_hex("#857c72")
    roles[MaterialRole.ON_SURFACE] = Color.from_hex("#ece5dc")
    roles[MaterialRole.PRIMARY] = Color.from_hex("#2b2723")
    dark = Mode(mode=ModeName.DARK, roles=roles, palettes=theme.dark.palettes)
    return replace(theme, dark=dark)


def old_recipe_saturation(primary: Color) -> float:
    _hue, _lightness, saturation = hls(primary)
    if saturation <= 1e-6:
        return 0.60
    return max(0.45, min(0.85, saturation))


def test_recipe_metadata_is_pinned() -> None:
    assert dict(ANSI_SLOT_ROLES) == {
        0: MaterialRole.SURFACE,
        7: MaterialRole.ON_SURFACE_VARIANT,
        8: MaterialRole.OUTLINE_VARIANT,
        15: MaterialRole.ON_SURFACE,
    }
    # Slots 1..6 in standard ANSI order: red, green, yellow, blue, magenta, cyan.
    assert dict(ANSI_HUE_ANCHORS) == {
        1: 25.0,
        2: 145.0,
        3: 90.0,
        4: 260.0,
        5: 330.0,
        6: 200.0,
    }
    assert ANSI_HUE_TINT_MAX == pytest.approx(0.30)
    assert ANSI_HUE_TINT_STEP == pytest.approx(0.01)
    assert ANSI_HUE_FAMILY_BOUND == pytest.approx(25.0)
    assert ANSI_MIN_HUE_SEPARATION == pytest.approx(40.0)
    assert ANSI_NORMAL_LIGHTNESS[ModeName.DARK] == pytest.approx(0.55)
    assert ANSI_NORMAL_LIGHTNESS[ModeName.LIGHT] == pytest.approx(0.45)
    assert ANSI_BRIGHT_LIGHTNESS[ModeName.DARK] == pytest.approx(0.72)
    assert ANSI_BRIGHT_LIGHTNESS[ModeName.LIGHT] == pytest.approx(0.60)
    assert ANSI_SATURATION_MIN == pytest.approx(0.35)
    assert ANSI_SATURATION_MAX == pytest.approx(0.65)
    assert ANSI_SATURATION_FALLBACK == pytest.approx(0.50)


def test_palette_has_sixteen_colors_and_is_deterministic() -> None:
    theme = load_theme()

    first = ansi_palette(theme)
    second = ansi_palette(theme)

    assert len(first) == ANSI_COLOR_COUNT
    assert all(isinstance(color, Color) for color in first)
    assert first == second


def test_zero_seven_eight_fifteen_track_material_roles() -> None:
    theme = load_theme()
    palette = ansi_palette(theme)

    assert palette[0] == theme.dark.roles[MaterialRole.SURFACE]
    assert palette[7] == theme.dark.roles[MaterialRole.ON_SURFACE_VARIANT]
    assert palette[8] == theme.dark.roles[MaterialRole.OUTLINE_VARIANT]
    assert palette[15] == theme.dark.roles[MaterialRole.ON_SURFACE]


def test_chromatic_slots_stay_in_their_ansi_family() -> None:
    palette = ansi_palette(load_theme())

    for slot, anchor in ANSI_HUE_ANCHORS.items():
        assert in_family(palette[slot], anchor), slot
        assert in_family(palette[slot + 8], anchor), slot + 8


def test_warm_and_cool_primaries_tint_hues_toward_the_primary() -> None:
    for target_hue in (10.0, 220.0):
        theme = primary_hue_theme(target_hue)
        palette = ansi_palette(theme)
        actual_primary_hue = primary_hue(theme)

        for slot, anchor in ANSI_HUE_ANCHORS.items():
            tinted = hue_degrees(palette[slot])
            assert (
                circular_distance(tinted, anchor)
                <= ANSI_HUE_FAMILY_BOUND + QUANTIZATION_TOLERANCE
            )
            assert circular_distance(tinted, actual_primary_hue) < circular_distance(
                anchor, actual_primary_hue
            ), slot


@pytest.mark.parametrize(
    "primary",
    [
        0.0,
        25.0,
        90.0,
        117.5,
        145.0,
        180.0,
        200.0,
        205.0,
        240.0,
        260.0,
        300.0,
        330.0,
        359.0,
    ],
)
def test_minimum_separation_holds_for_adversarial_primaries(primary: float) -> None:
    palette = ansi_palette(primary_hue_theme(primary))
    hues = [hue_degrees(palette[slot]) for slot in range(1, 7)]

    for index, first in enumerate(hues):
        for second in hues[index + 1 :]:
            # RGB quantisation may move a hue by a fraction of a degree.
            assert circular_distance(first, second) >= ANSI_MIN_HUE_SEPARATION - 0.5
    assert len(set(palette[1:7])) == 6


def test_separation_rule_lowers_the_shared_tint_factor() -> None:
    primary_hue = 117.5  # Midpoint of the yellow (90) and green (145) anchors.
    hues = _tinted_hues(primary_hue)
    yellow_anchor = ANSI_HUE_ANCHORS[3]
    effective_factor = circular_distance(hues[3], yellow_anchor) / circular_distance(
        yellow_anchor, primary_hue
    )

    assert effective_factor < ANSI_HUE_TINT_MAX
    assert effective_factor == pytest.approx(0.27)
    values = tuple(hues.values())
    assert min(
        circular_distance(first, second)
        for index, first in enumerate(values)
        for second in values[index + 1 :]
    ) >= ANSI_MIN_HUE_SEPARATION


def test_bright_slots_are_brighter_and_follow_their_normal_slot() -> None:
    palette = ansi_palette(load_theme())

    for slot in range(1, 7):
        normal = hls(palette[slot])
        bright = hls(palette[slot + 8])
        assert bright[1] > normal[1], slot
        # Same tinted hue: rounding permits a fraction of a degree of drift.
        delta = circular_distance(bright[0] * 360.0, normal[0] * 360.0)
        assert delta < 2.0, slot


def test_dark_mode_uses_the_dark_lightness_recipe() -> None:
    palette = ansi_palette(load_theme(), ModeName.DARK)

    for slot in range(1, 7):
        assert hls(palette[slot])[1] == pytest.approx(0.55, abs=0.01)
        assert hls(palette[slot + 8])[1] == pytest.approx(0.72, abs=0.01)


def test_light_mode_uses_light_recipe_and_light_roles() -> None:
    theme = load_theme()
    palette = ansi_palette(theme, ModeName.LIGHT)

    assert palette[0] == theme.light.roles[MaterialRole.SURFACE]
    assert palette[15] == theme.light.roles[MaterialRole.ON_SURFACE]
    for slot in range(1, 7):
        normal_lightness = hls(palette[slot])[1]
        bright_lightness = hls(palette[slot + 8])[1]
        assert normal_lightness == pytest.approx(0.45, abs=0.01)
        assert bright_lightness == pytest.approx(0.60, abs=0.01)


def test_low_chroma_theme_still_yields_sixteen_distinct_colors() -> None:
    palette = ansi_palette(low_chroma_theme())

    assert len(set(palette)) == 16
    assert len(set(palette[1:7])) == 6
    assert len(set(palette[9:15])) == 6
    # Minimum saturation keeps the hue anchors separated even at low chroma.
    for slot in range(1, 7):
        assert hls(palette[slot])[2] >= ANSI_SATURATION_MIN - 0.01


def test_achromatic_primary_uses_saturation_fallback_and_no_hue_tint() -> None:
    theme = mutate_role(load_theme(), "primary", "#808080")
    palette = ansi_palette(theme)

    assert len(set(palette[1:7])) == 6
    for slot, anchor in ANSI_HUE_ANCHORS.items():
        assert hue_degrees(palette[slot]) == pytest.approx(anchor, abs=0.5)
        assert hue_degrees(palette[slot + 8]) == pytest.approx(anchor, abs=0.5)
        assert hls(palette[slot])[2] == pytest.approx(ANSI_SATURATION_FALLBACK, abs=0.01)
        assert hls(palette[slot + 8])[2] == pytest.approx(
            ANSI_SATURATION_FALLBACK, abs=0.01
        )


def test_primary_saturation_is_clamped_to_the_new_window() -> None:
    low = ansi_palette(mutate_role(load_theme(), "primary", "#26201a"))
    high = ansi_palette(mutate_role(load_theme(), "primary", "#ff0000"))

    for slot in range(1, 7):
        assert hls(low[slot])[2] == pytest.approx(ANSI_SATURATION_MIN, abs=0.01)
        assert hls(high[slot])[2] == pytest.approx(ANSI_SATURATION_MAX, abs=0.01)
        assert (
            ANSI_SATURATION_MIN - 0.01
            <= hls(high[slot + 8])[2]
            <= ANSI_SATURATION_MAX + 0.01
        )


@pytest.mark.parametrize("primary_hex", ["#ff0000", "#26201a", "#808080"])
def test_saturation_is_lower_than_the_old_recipe(primary_hex: str) -> None:
    theme = mutate_role(load_theme(), "primary", primary_hex)
    palette = ansi_palette(theme)
    old = old_recipe_saturation(Color.from_hex(primary_hex))

    for slot in range(1, 7):
        new = hls(palette[slot])[2]
        assert ANSI_SATURATION_MIN - 0.01 <= new <= ANSI_SATURATION_MAX + 0.01
        assert new < old


def test_unrelated_role_mutation_does_not_change_ansi() -> None:
    theme = load_theme()
    mutated = mutate_role(theme, "inverse_primary", "#123456")

    assert ansi_palette(mutated) == ansi_palette(theme)


def test_primary_saturation_mutation_changes_ansi() -> None:
    theme = load_theme()
    desaturated = mutate_role(theme, "primary", "#2b2723")
    saturated = mutate_role(theme, "primary", "#ff0000")

    before = ansi_palette(desaturated)
    after = ansi_palette(saturated)

    assert before != after
    assert all(before[slot] != after[slot] for slot in range(1, 7))
