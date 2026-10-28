"""Enumerations and fixed vocabularies for the Theme domain model."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "MaterialRole",
    "ModeName",
    "PaletteName",
    "SourceKind",
    "TONE_ORDER",
    "TONES",
]


class MaterialRole(StrEnum):
    """The 50 Material 3 color roles emitted by matugen 4.2.0."""

    BACKGROUND = "background"
    ERROR = "error"
    ERROR_CONTAINER = "error_container"
    INVERSE_ON_SURFACE = "inverse_on_surface"
    INVERSE_PRIMARY = "inverse_primary"
    INVERSE_SURFACE = "inverse_surface"
    ON_BACKGROUND = "on_background"
    ON_ERROR = "on_error"
    ON_ERROR_CONTAINER = "on_error_container"
    ON_PRIMARY = "on_primary"
    ON_PRIMARY_CONTAINER = "on_primary_container"
    ON_PRIMARY_FIXED = "on_primary_fixed"
    ON_PRIMARY_FIXED_VARIANT = "on_primary_fixed_variant"
    ON_SECONDARY = "on_secondary"
    ON_SECONDARY_CONTAINER = "on_secondary_container"
    ON_SECONDARY_FIXED = "on_secondary_fixed"
    ON_SECONDARY_FIXED_VARIANT = "on_secondary_fixed_variant"
    ON_SURFACE = "on_surface"
    ON_SURFACE_VARIANT = "on_surface_variant"
    ON_TERTIARY = "on_tertiary"
    ON_TERTIARY_CONTAINER = "on_tertiary_container"
    ON_TERTIARY_FIXED = "on_tertiary_fixed"
    ON_TERTIARY_FIXED_VARIANT = "on_tertiary_fixed_variant"
    OUTLINE = "outline"
    OUTLINE_VARIANT = "outline_variant"
    PRIMARY = "primary"
    PRIMARY_CONTAINER = "primary_container"
    PRIMARY_FIXED = "primary_fixed"
    PRIMARY_FIXED_DIM = "primary_fixed_dim"
    SCRIM = "scrim"
    SECONDARY = "secondary"
    SECONDARY_CONTAINER = "secondary_container"
    SECONDARY_FIXED = "secondary_fixed"
    SECONDARY_FIXED_DIM = "secondary_fixed_dim"
    SHADOW = "shadow"
    SOURCE_COLOR = "source_color"
    SURFACE = "surface"
    SURFACE_BRIGHT = "surface_bright"
    SURFACE_CONTAINER = "surface_container"
    SURFACE_CONTAINER_HIGH = "surface_container_high"
    SURFACE_CONTAINER_HIGHEST = "surface_container_highest"
    SURFACE_CONTAINER_LOW = "surface_container_low"
    SURFACE_CONTAINER_LOWEST = "surface_container_lowest"
    SURFACE_DIM = "surface_dim"
    SURFACE_TINT = "surface_tint"
    SURFACE_VARIANT = "surface_variant"
    TERTIARY = "tertiary"
    TERTIARY_CONTAINER = "tertiary_container"
    TERTIARY_FIXED = "tertiary_fixed"
    TERTIARY_FIXED_DIM = "tertiary_fixed_dim"


class PaletteName(StrEnum):
    """The six Material tonal palettes in every mode."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    NEUTRAL = "neutral"
    NEUTRAL_VARIANT = "neutral_variant"
    ERROR = "error"


class SourceKind(StrEnum):
    """How the seed for a Theme was supplied."""

    IMAGE = "image"
    COLOR = "color"
    JSON = "json"


class ModeName(StrEnum):
    """The two color modes present in every Theme."""

    DARK = "dark"
    LIGHT = "light"


# Exactly the 18 tones matugen 4.2.0 emits for each tonal palette.
TONES: frozenset[int] = frozenset(
    {0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 95, 98, 99, 100}
)

# Stable ascending order, used for deterministic serialization.
TONE_ORDER: tuple[int, ...] = tuple(sorted(TONES))
