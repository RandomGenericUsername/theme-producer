"""Deliberate 16-color ANSI palette recipe.

ANSI is a projection, not part of the Theme domain model. This module is a pure
function of a :class:`~theme_producer.domain.models.Theme` and produces the one
shared 16-color table consumed by both the kitty and OSC-sequences projections
(REQ-009, CAP-008, AD-6).

The recipe is deliberately hue-anchored; it is not a luminance ramp and not
base16 ordering. The six chromatic slots use fixed hue anchors in standard ANSI
order, while tone and chroma come from the theme:

===========  ==========  ==========================
slot         anchor      hue (degrees)
===========  ==========  ==========================
1            red         25
2            green       145
3            yellow      90
4            blue        260
5            magenta     330
6            cyan        200
===========  ==========  ==========================

* ``color0`` is Material ``surface``; ``color7`` is ``on_surface_variant``;
  ``color8`` is ``outline_variant``; ``color15`` is ``on_surface``.
* ``color9``..``color14`` are the bright variants of ``color1``..``color6``:
  same hue anchor, higher lightness.
* Normal lightness is ``0.55`` in dark mode and ``0.45`` in light mode; bright
  lightness is ``0.72`` (dark) and ``0.60`` (light).
* Saturation is derived from the theme's ``primary`` via :func:`colorsys.rgb_to_hls`,
  clamped to ``[0.45, 0.85]``. An achromatic primary (HLS saturation ``0``)
  falls back to ``0.60``.

Because every chromatic slot has a distinct hue anchor and a minimum saturation,
a low-chroma theme cannot collapse the twelve generated slots into one color.

Evidence: ``tickets/req-009-ansi-projection/ticket.md``; spec CAP-008;
architecture AD-6.
"""

from __future__ import annotations

import colorsys
from collections.abc import Mapping
from types import MappingProxyType

from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Mode, Theme

__all__ = [
    "ANSI_BRIGHT_LIGHTNESS",
    "ANSI_COLOR_COUNT",
    "ANSI_HUE_ANCHORS",
    "ANSI_NORMAL_LIGHTNESS",
    "ANSI_SATURATION_FALLBACK",
    "ANSI_SATURATION_MAX",
    "ANSI_SATURATION_MIN",
    "ANSI_SLOT_ROLES",
    "ansi_palette",
]

#: A complete ANSI table always has exactly sixteen slots.
ANSI_COLOR_COUNT = 16

#: Non-generated slots keep their Material meaning instead of a hue ramp.
ANSI_SLOT_ROLES: Mapping[int, MaterialRole] = MappingProxyType(
    {
        0: MaterialRole.SURFACE,
        7: MaterialRole.ON_SURFACE_VARIANT,
        8: MaterialRole.OUTLINE_VARIANT,
        15: MaterialRole.ON_SURFACE,
    }
)

#: Fixed hue anchors for slots 1..6 in standard ANSI order
#: (red, green, yellow, blue, magenta, cyan).
ANSI_HUE_ANCHORS: Mapping[int, float] = MappingProxyType(
    {
        1: 25.0,
        2: 145.0,
        3: 90.0,
        4: 260.0,
        5: 330.0,
        6: 200.0,
    }
)

#: Slots 9..14 are the bright variants of slots 1..6.
ANSI_BRIGHT_OFFSET = 8

#: Per-mode lightness for the normal and bright chromatic slots.
ANSI_NORMAL_LIGHTNESS: Mapping[ModeName, float] = MappingProxyType(
    {
        ModeName.DARK: 0.55,
        ModeName.LIGHT: 0.45,
    }
)
ANSI_BRIGHT_LIGHTNESS: Mapping[ModeName, float] = MappingProxyType(
    {
        ModeName.DARK: 0.72,
        ModeName.LIGHT: 0.60,
    }
)

#: Saturation window derived from the theme's ``primary``.
ANSI_SATURATION_MIN = 0.45
ANSI_SATURATION_MAX = 0.85
ANSI_SATURATION_FALLBACK = 0.60

#: HLS saturation below this counts as achromatic.
_ACHROMATIC_EPSILON = 1e-6


def _mode_and_name(theme: Theme, mode: ModeName | str) -> tuple[Mode, ModeName]:
    mode_name = ModeName(mode)
    selected = theme.dark if mode_name is ModeName.DARK else theme.light
    return selected, mode_name


def _primary_saturation(mode: Mode) -> float:
    primary = mode.roles[MaterialRole.PRIMARY]
    _hue, _lightness, saturation = colorsys.rgb_to_hls(
        *(channel / 255.0 for channel in primary.rgb)
    )
    if saturation <= _ACHROMATIC_EPSILON:
        return ANSI_SATURATION_FALLBACK
    return max(ANSI_SATURATION_MIN, min(ANSI_SATURATION_MAX, saturation))


def _hue_color(hue: float, lightness: float, saturation: float) -> Color:
    red, green, blue = colorsys.hls_to_rgb(hue / 360.0, lightness, saturation)
    return Color.from_rgb(red * 255.0, green * 255.0, blue * 255.0)


def ansi_palette(theme: Theme, mode: ModeName | str = ModeName.DARK) -> tuple[Color, ...]:
    """Return the deterministic 16-color ANSI table for ``theme``.

    ``mode`` defaults to dark because the projection catalog renders the dark
    mode; passing ``ModeName.LIGHT`` applies the light-mode lightness recipe.
    """
    selected, mode_name = _mode_and_name(theme, mode)
    saturation = _primary_saturation(selected)
    normal_lightness = ANSI_NORMAL_LIGHTNESS[mode_name]
    bright_lightness = ANSI_BRIGHT_LIGHTNESS[mode_name]

    colors: dict[int, Color] = {
        index: selected.roles[role] for index, role in ANSI_SLOT_ROLES.items()
    }
    for index, hue in ANSI_HUE_ANCHORS.items():
        colors[index] = _hue_color(hue, normal_lightness, saturation)
        colors[index + ANSI_BRIGHT_OFFSET] = _hue_color(hue, bright_lightness, saturation)

    return tuple(colors[index] for index in range(ANSI_COLOR_COUNT))
