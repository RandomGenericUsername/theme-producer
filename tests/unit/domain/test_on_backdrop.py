from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from theme_producer.domain.color_metrics import contrast_ratio, relative_luminance
from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme
from theme_producer.domain.on_backdrop import (
    ON_BACKDROP_CANDIDATES,
    apply_on_backdrop,
    select_on_backdrop,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def mode_with_roles(mode: Mode, colors: dict[MaterialRole, str]) -> Mode:
    roles = dict(mode.roles)
    for role, value in colors.items():
        roles[role] = Color.from_hex(value)
    return Mode(mode=mode.mode, roles=roles, palettes=mode.palettes, on_backdrop=mode.on_backdrop)


def test_candidate_set_is_the_documented_neutral_pole() -> None:
    assert ON_BACKDROP_CANDIDATES == (
        MaterialRole.ON_SURFACE,
        MaterialRole.ON_SURFACE_VARIANT,
        MaterialRole.ON_BACKGROUND,
        MaterialRole.INVERSE_ON_SURFACE,
        MaterialRole.INVERSE_SURFACE,
        MaterialRole.OUTLINE,
        MaterialRole.OUTLINE_VARIANT,
        MaterialRole.SURFACE,
        MaterialRole.SURFACE_DIM,
        MaterialRole.SURFACE_CONTAINER_LOWEST,
    )


def test_bright_band_selects_a_dark_candidate() -> None:
    theme = load_theme()
    dark = mode_with_roles(
        theme.dark,
        {
            MaterialRole.ON_SURFACE: "#fbd0aa",
            MaterialRole.ON_SURFACE_VARIANT: "#d8c2af",
            MaterialRole.ON_BACKGROUND: "#fbd0aa",
            MaterialRole.INVERSE_ON_SURFACE: "#3a2f28",
            MaterialRole.INVERSE_SURFACE: "#f0e0d2",
            MaterialRole.OUTLINE: "#9a8c80",
            MaterialRole.OUTLINE_VARIANT: "#4e453d",
            MaterialRole.SURFACE: "#0d0b09",
            MaterialRole.SURFACE_DIM: "#14110e",
            MaterialRole.SURFACE_CONTAINER_LOWEST: "#000000",
        },
    )

    selected = select_on_backdrop(dark, 1.0)

    assert relative_luminance(selected) < 0.1
    assert contrast_ratio(relative_luminance(selected), 1.0) >= 4.5


def test_dark_band_selects_a_light_candidate() -> None:
    theme = load_theme()
    light = mode_with_roles(
        theme.light,
        {
            MaterialRole.ON_SURFACE: "#3a2f28",
            MaterialRole.ON_SURFACE_VARIANT: "#5a4f46",
            MaterialRole.ON_BACKGROUND: "#3a2f28",
            MaterialRole.INVERSE_ON_SURFACE: "#fbd0aa",
            MaterialRole.INVERSE_SURFACE: "#3a2f28",
            MaterialRole.OUTLINE: "#7a6d62",
            MaterialRole.OUTLINE_VARIANT: "#c0b3a6",
            MaterialRole.SURFACE: "#fff8f2",
            MaterialRole.SURFACE_DIM: "#f0e6de",
            MaterialRole.SURFACE_CONTAINER_LOWEST: "#ffffff",
        },
    )

    selected = select_on_backdrop(light, 0.0)

    assert relative_luminance(selected) > 0.9
    assert contrast_ratio(relative_luminance(selected), 0.0) >= 4.5


def test_band_scheme_disagreement_is_allowed_to_cross_the_ink_pole() -> None:
    theme = load_theme()
    dark_scheme = theme.dark
    assert relative_luminance(dark_scheme.roles[MaterialRole.ON_SURFACE]) > 0.5
    assert relative_luminance(dark_scheme.roles[MaterialRole.SURFACE]) < 0.1

    # Dark scheme, bright band: the wallpaper disagrees with the scheme, so the
    # produced role sits on the opposite pole from on_surface.
    applied = apply_on_backdrop(theme, 1.0).dark

    assert applied.on_backdrop is not None
    assert relative_luminance(applied.on_backdrop) < relative_luminance(
        applied.roles[MaterialRole.ON_SURFACE]
    )
    assert relative_luminance(applied.on_backdrop) < 0.5


def test_mid_gray_band_is_best_effort_below_wcag_45() -> None:
    theme = load_theme()
    band = 0.18
    muted = mode_with_roles(
        theme.dark,
        {
            MaterialRole.ON_SURFACE: "#777777",
            MaterialRole.ON_SURFACE_VARIANT: "#666666",
            MaterialRole.ON_BACKGROUND: "#888888",
            MaterialRole.INVERSE_ON_SURFACE: "#767676",
            MaterialRole.INVERSE_SURFACE: "#858585",
            MaterialRole.OUTLINE: "#656565",
            MaterialRole.OUTLINE_VARIANT: "#8a8a8a",
            MaterialRole.SURFACE: "#757575",
            MaterialRole.SURFACE_DIM: "#808080",
            MaterialRole.SURFACE_CONTAINER_LOWEST: "#6f6f6f",
        },
    )

    selected = select_on_backdrop(muted, band)
    best_ratio = max(
        contrast_ratio(relative_luminance(muted.roles[role]), band)
        for role in ON_BACKDROP_CANDIDATES
    )

    assert contrast_ratio(relative_luminance(selected), band) == pytest.approx(best_ratio)
    assert best_ratio < 4.5


def test_ties_prefer_on_surface() -> None:
    theme = load_theme()
    tied = mode_with_roles(
        theme.dark,
        {role: "#808080" for role in ON_BACKDROP_CANDIDATES},
    )

    assert select_on_backdrop(tied, 0.2) == tied.roles[MaterialRole.ON_SURFACE]


def test_apply_selects_independently_for_both_modes() -> None:
    applied = apply_on_backdrop(load_theme(), 1.0)

    assert applied.dark.mode is ModeName.DARK
    assert applied.light.mode is ModeName.LIGHT
    assert applied.dark.on_backdrop is not None
    assert applied.light.on_backdrop is not None


def test_engine_independence_same_band_and_roles_give_the_same_role() -> None:
    theme = load_theme()
    other_engine = replace(
        theme,
        generator=replace(theme.generator, engine="native", engine_version="0.1.0"),
    )

    matugen = apply_on_backdrop(theme, 0.9)
    native = apply_on_backdrop(other_engine, 0.9)

    assert matugen.dark.on_backdrop == native.dark.on_backdrop
    assert matugen.light.on_backdrop == native.light.on_backdrop
