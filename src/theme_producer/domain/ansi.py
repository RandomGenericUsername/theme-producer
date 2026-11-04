"""Deliberate 16-color ANSI palette recipe.

ANSI is a projection, not part of the Theme domain model. This module is a pure
function of a :class:`~theme_producer.domain.models.Theme` and produces the one
shared 16-color table consumed by both the kitty and OSC-sequences projections
(REQ-009, CAP-008, AD-6). REQ-023 makes the six chromatic slots theme-tinted
instead of a fixed rainbow.

The recipe is deliberately hue-anchored; it is not a luminance ramp and not
base16 ordering. The six chromatic slots keep their standard ANSI hue families
and are tinted part-way toward the theme's ``primary`` hue:

===========  ==========  ======================  =============
slot         family       anchor (degrees)        family bound
===========  ==========  ======================  =============
1            red         25                      25 degrees
2            green       145                     25 degrees
3            yellow      90                      25 degrees
4            blue        260                     25 degrees
5            magenta     330                     25 degrees
6            cyan        200                     25 degrees
===========  ==========  ======================  =============

Hue rule (normative constants below):

* Move each anchor toward the primary's HLS hue along the shortest circular arc
  by ``ANSI_HUE_TINT_MAX`` (30%). Clamp the total movement from the anchor to
  ``ANSI_HUE_FAMILY_BOUND`` (25 degrees), so an opposite-hue primary cannot turn
  red into cyan. The bound applies to the generated hue; measuring a stored
  8-bit RGB value can add about a degree of rounding. An achromatic primary has
  no meaningful hue and applies no tint.
* Enforce at least ``ANSI_MIN_HUE_SEPARATION`` (40 degrees) of shortest circular
  distance between every pair of tinted hues. When a blend violates that, lower
  the shared blend factor by ``ANSI_HUE_TINT_STEP`` (0.01) and retry, down to
  ``0.0`` (the untilted anchors). The original anchors are 55-70 degrees apart,
  so the loop always terminates. Reducing one shared factor keeps the six slots
  coherent; the result is deterministic.

* ``color0`` is Material ``surface``; ``color7`` is ``on_surface_variant``;
  ``color8`` is ``outline_variant``; ``color15`` is ``on_surface``.
* ``color9``..``color14`` are the bright variants of ``color1``..``color6``:
  same tinted hue, higher lightness.
* Normal lightness is ``0.55`` in dark mode and ``0.45`` in light mode; bright
  lightness is ``0.72`` (dark) and ``0.60`` (light).
* Saturation is derived from the theme's ``primary`` via :func:`colorsys.rgb_to_hls`,
  clamped to the calmer ``[0.35, 0.65]`` window. An achromatic primary (HLS
  saturation ``0``) falls back to ``0.50``.

Because every chromatic slot keeps a distinct hue family, a bounded drift from
its anchor, and a minimum pairwise separation, a low-chroma theme cannot collapse
the twelve generated slots into one color.

Evidence: ``tickets/req-009-ansi-projection/ticket.md`` and
``tickets/req-023-themed-ansi-anchors/ticket.md``; spec CAP-008; architecture
AD-6.
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
    "ANSI_HUE_FAMILY_BOUND",
    "ANSI_HUE_TINT_MAX",
    "ANSI_HUE_TINT_STEP",
    "ANSI_MIN_HUE_SEPARATION",
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

#: Maximum fraction of the shortest anchor-to-primary arc applied per slot.
ANSI_HUE_TINT_MAX = 0.30

#: Step used when the separation rule has to lower the shared blend factor.
ANSI_HUE_TINT_STEP = 0.01

#: Maximum distance a slot may drift from its own anchor, preserving its family.
ANSI_HUE_FAMILY_BOUND = 25.0

#: Minimum shortest circular distance required between any two tinted anchors.
ANSI_MIN_HUE_SEPARATION = 40.0

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

#: Calmer saturation window derived from the theme's ``primary``.
ANSI_SATURATION_MIN = 0.35
ANSI_SATURATION_MAX = 0.65
ANSI_SATURATION_FALLBACK = 0.50

#: HLS saturation below this counts as achromatic.
_ACHROMATIC_EPSILON = 1e-6

#: Float tolerance for the separation check.
_SEPARATION_EPSILON = 1e-9


def _mode_and_name(theme: Theme, mode: ModeName | str) -> tuple[Mode, ModeName]:
    mode_name = ModeName(mode)
    selected = theme.dark if mode_name is ModeName.DARK else theme.light
    return selected, mode_name


def _primary_hls(mode: Mode) -> tuple[float, float]:
    """Return the primary's hue in degrees and its HLS saturation."""
    primary = mode.roles[MaterialRole.PRIMARY]
    hue, _lightness, saturation = colorsys.rgb_to_hls(
        *(channel / 255.0 for channel in primary.rgb)
    )
    return hue * 360.0, saturation


def _primary_saturation(saturation: float) -> float:
    if saturation <= _ACHROMATIC_EPSILON:
        return ANSI_SATURATION_FALLBACK
    return max(ANSI_SATURATION_MIN, min(ANSI_SATURATION_MAX, saturation))


def _hue_color(hue: float, lightness: float, saturation: float) -> Color:
    red, green, blue = colorsys.hls_to_rgb(hue / 360.0, lightness, saturation)
    return Color.from_rgb(red * 255.0, green * 255.0, blue * 255.0)


def _shortest_delta(start: float, end: float) -> float:
    """Signed shortest angular distance from ``start`` to ``end`` in degrees."""
    return (end - start + 180.0) % 360.0 - 180.0


def _circular_distance(first: float, second: float) -> float:
    """Unsigned shortest angular distance between two hues in degrees."""
    return abs(_shortest_delta(first, second))


def _tinted_hue(anchor: float, primary_hue: float, factor: float) -> float:
    """Blend one anchor toward the primary, clamped to its family bound."""
    movement = _shortest_delta(anchor, primary_hue) * factor
    movement = max(-ANSI_HUE_FAMILY_BOUND, min(ANSI_HUE_FAMILY_BOUND, movement))
    return (anchor + movement) % 360.0


def _minimum_separation(hues: tuple[float, ...]) -> float:
    return min(
        _circular_distance(first, second)
        for index, first in enumerate(hues)
        for second in hues[index + 1 :]
    )


def _tinted_hues(primary_hue: float | None) -> dict[int, float]:
    """Return slot -> hue, lowering the shared tint until separation holds."""
    if primary_hue is None:
        return dict(ANSI_HUE_ANCHORS)

    steps = round(ANSI_HUE_TINT_MAX / ANSI_HUE_TINT_STEP)
    for step in range(steps, -1, -1):
        factor = step * ANSI_HUE_TINT_STEP
        hues = {
            slot: _tinted_hue(anchor, primary_hue, factor)
            for slot, anchor in ANSI_HUE_ANCHORS.items()
        }
        if _minimum_separation(tuple(hues.values())) + _SEPARATION_EPSILON >= (
            ANSI_MIN_HUE_SEPARATION
        ):
            return hues

    # Unreachable: factor 0 returns the untilted anchors, which satisfy the rule.
    return dict(ANSI_HUE_ANCHORS)


def ansi_palette(theme: Theme, mode: ModeName | str = ModeName.DARK) -> tuple[Color, ...]:
    """Return the deterministic 16-color ANSI table for ``theme``.

    ``mode`` defaults to dark because the projection catalog renders the dark
    mode; passing ``ModeName.LIGHT`` applies the light-mode lightness recipe.
    """
    selected, mode_name = _mode_and_name(theme, mode)
    primary_hue, primary_saturation = _primary_hls(selected)
    saturation = _primary_saturation(primary_saturation)
    normal_lightness = ANSI_NORMAL_LIGHTNESS[mode_name]
    bright_lightness = ANSI_BRIGHT_LIGHTNESS[mode_name]

    tintable_hue = None if primary_saturation <= _ACHROMATIC_EPSILON else primary_hue
    hues = _tinted_hues(tintable_hue)

    colors: dict[int, Color] = {
        index: selected.roles[role] for index, role in ANSI_SLOT_ROLES.items()
    }
    for index, hue in hues.items():
        colors[index] = _hue_color(hue, normal_lightness, saturation)
        colors[index + ANSI_BRIGHT_OFFSET] = _hue_color(hue, bright_lightness, saturation)

    return tuple(colors[index] for index in range(ANSI_COLOR_COUNT))
