"""Wallpaper-derived 16-color ANSI palette projection.

ANSI is a projection, not part of the Theme domain model. This module is a pure
function of a :class:`~theme_producer.domain.models.Theme` and produces the one
shared 16-color table consumed by both the kitty and OSC-sequences projections
(REQ-009, CAP-008, AD-6).

REQ-023 tinted six fixed ANSI hue anchors toward the primary. REQ-024 supersedes
that recipe: every one of the sixteen slots is now a Material role from the
selected mode, so the terminal palette is fully wallpaper/palette-derived and
contains no invented hue. The slot order is the canonical legacy alias order
(:data:`theme_producer.domain.services.LEGACY_COLOR_ORDER`), which is also the
order of the palette's ``colors`` list in the named projections.

.. code-block:: text

    slot  role
    ----  ----------------------
    0     surface
    1     error
    2     tertiary
    3     secondary
    4     primary
    5     surface_variant
    6     outline_variant
    7     on_surface
    8     outline
    9     error_container
    10    tertiary_container
    11    secondary_container
    12    primary_container
    13    surface_container
    14    surface_container_high
    15    on_surface_variant

Tradeoff (JD-approved): standard ANSI red/green/blue semantics are no longer
preserved. A slot tracks its role instead, so the terminal matches the wallpaper
rather than a fixed rainbow. Duplicate values are valid when two roles coincide
(e.g. a low-chroma theme where ``surface`` and ``surface_container`` are equal);
the recipe never fabricates a color to keep slots distinct.

Evidence: ``tickets/req-009-ansi-projection/ticket.md``,
``tickets/req-023-themed-ansi-anchors/ticket.md`` (superseded), and
``tickets/req-024-role-derived-ansi/ticket.md``; spec CAP-008; architecture AD-6.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from theme_producer.domain.enums import MaterialRole, ModeName
from theme_producer.domain.models import Color, Theme

__all__ = [
    "ANSI_COLOR_COUNT",
    "ANSI_SLOT_ROLES",
    "ansi_palette",
]

#: A complete ANSI table always has exactly sixteen slots.
ANSI_COLOR_COUNT = 16

#: Every ANSI slot maps directly to one Material role in canonical legacy order.
ANSI_SLOT_ROLES: Mapping[int, MaterialRole] = MappingProxyType(
    {
        0: MaterialRole.SURFACE,
        1: MaterialRole.ERROR,
        2: MaterialRole.TERTIARY,
        3: MaterialRole.SECONDARY,
        4: MaterialRole.PRIMARY,
        5: MaterialRole.SURFACE_VARIANT,
        6: MaterialRole.OUTLINE_VARIANT,
        7: MaterialRole.ON_SURFACE,
        8: MaterialRole.OUTLINE,
        9: MaterialRole.ERROR_CONTAINER,
        10: MaterialRole.TERTIARY_CONTAINER,
        11: MaterialRole.SECONDARY_CONTAINER,
        12: MaterialRole.PRIMARY_CONTAINER,
        13: MaterialRole.SURFACE_CONTAINER,
        14: MaterialRole.SURFACE_CONTAINER_HIGH,
        15: MaterialRole.ON_SURFACE_VARIANT,
    }
)


def ansi_palette(theme: Theme, mode: ModeName | str = ModeName.DARK) -> tuple[Color, ...]:
    """Return the deterministic 16-color ANSI table for ``theme``.

    ``mode`` defaults to dark because the projection catalog renders the dark
    mode; passing ``ModeName.LIGHT`` selects the light mode's roles.
    """
    mode_name = ModeName(mode)
    selected = theme.dark if mode_name is ModeName.DARK else theme.light
    return tuple(
        selected.roles[ANSI_SLOT_ROLES[index]] for index in range(ANSI_COLOR_COUNT)
    )
