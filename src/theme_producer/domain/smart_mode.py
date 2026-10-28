"""Smart projection policy: pick ``dark`` or ``light`` from source luminance.

This is a *projection* policy, not a color-generation mode.  The engine always
produces both Theme modes; smart mode only decides which concrete mode the
consumer projections render.  It is deliberately not matugen's
``--mode smart``: matugen picked dark on the whole real wallpaper corpus,
including bright synthetic images.

Formula
-------
Pillow decodes the image and converts it to 8-bit sRGB (``RGB``).  Each
channel is linearized with the sRGB transfer function::

    lin(c) = c / 12.92                         if c <= 0.04045
    lin(c) = ((c + 0.055) / 1.055) ** 2.4      otherwise

where ``c`` is the channel value in ``[0, 1]`` (``byte / 255``).  The mean
relative luminance of the image is the average of every linearized channel
over every pixel::

    L = mean( (lin(R) + lin(G) + lin(B)) / 3 )

so black is ``0``, white is ``1``, and a gray whose linear value is ``0.5``
(sRGB byte 188, roughly ``#bcbcbc``) measures ``0.5``.  A color source uses
the seed color's three channels in the same formula instead of an image.

Decision: ``smart`` renders ``light`` when ``L >= threshold`` and ``dark``
otherwise.  Both sides use the same configurable threshold (default ``0.5``).
"""

from __future__ import annotations

import math
from enum import StrEnum
from pathlib import Path

from PIL import Image, ImageStat, UnidentifiedImageError

from theme_producer.domain.enums import ModeName
from theme_producer.domain.generation import (
    InvalidSmartThresholdError,
    SmartModeError,
    UnknownModeError,
)
from theme_producer.domain.models import Color

__all__ = [
    "ProjectionMode",
    "image_mean_luminance",
    "mean_relative_luminance",
    "parse_projection_mode",
    "relative_luminance_from_hex",
    "resolve_projection_mode",
    "resolve_smart_mode",
    "validate_threshold",
]


class ProjectionMode(StrEnum):
    """The ``--mode`` vocabulary: two concrete modes plus the smart policy."""

    DARK = "dark"
    LIGHT = "light"
    SMART = "smart"


def _linearize(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


# Pillow maps 8-bit channels through a 256-entry lookup table in C.  Scaling the
# linear values back to 0..255 keeps the result an "L" image, which ImageStat
# reads cheaply without a per-pixel Python loop (8K wallpapers have ~33M pixels).
_LINEAR_LUT = tuple(round(_linearize(value / 255.0) * 255.0) for value in range(256))


def mean_relative_luminance(image: Image.Image) -> float:
    """Return the mean linearized-sRGB luminance of ``image`` in ``[0, 1]``."""
    rgb = image.convert("RGB")
    channel_means = [
        ImageStat.Stat(channel.point(_LINEAR_LUT)).mean[0] / 255.0 for channel in rgb.split()
    ]
    return sum(channel_means) / 3.0


def image_mean_luminance(path: Path | str) -> float:
    """Decode ``path`` with Pillow and return its mean relative luminance."""
    image_path = Path(path)
    try:
        with Image.open(image_path) as image:
            return mean_relative_luminance(image)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise SmartModeError(
            f"cannot decode image for smart mode: {image_path}: {exc}",
            details={"path": str(image_path)},
        ) from exc


def relative_luminance_from_hex(value: str) -> float:
    """Return the mean linearized-sRGB luminance of a ``#rrggbb`` seed color."""
    try:
        rgb = Color.from_hex(value).rgb
    except Exception as exc:  # ThemeValidationError; keep the CLI error typed
        raise SmartModeError(f"invalid seed color for smart mode: {value!r}") from exc
    assert rgb is not None
    return sum(_linearize(channel / 255.0) for channel in rgb) / 3.0


def validate_threshold(value: object) -> float:
    """Coerce and validate a smart threshold, raising a typed, clear error."""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise InvalidSmartThresholdError(
            f"smart threshold must be a number in [0, 1]; got {value!r}"
        )
    try:
        threshold = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidSmartThresholdError(
            f"smart threshold must be a number in [0, 1]; got {value!r}"
        ) from exc
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise InvalidSmartThresholdError(
            f"smart threshold must be a number in [0, 1]; got {value!r}"
        )
    return threshold


def resolve_smart_mode(luminance: float, threshold: float) -> ModeName:
    """Map a measured luminance to ``light`` (``>= threshold``) or ``dark``."""
    return ModeName.LIGHT if luminance >= threshold else ModeName.DARK


def parse_projection_mode(value: object) -> ProjectionMode:
    """Validate ``--mode``/``default_mode`` and return its enum member."""
    try:
        return ProjectionMode(str(value).strip().lower())
    except (TypeError, ValueError) as exc:
        raise UnknownModeError(
            f"unknown projection mode {value!r}; known modes: dark, light, smart"
        ) from exc


def resolve_projection_mode(
    mode: ProjectionMode | ModeName | str,
    *,
    image_path: Path | str | None = None,
    seed_color: str | None = None,
    threshold: object = 0.5,
) -> ModeName:
    """Resolve a (possibly smart) projection mode to a concrete Theme mode.

    ``smart`` measures the seed color when supplied, otherwise the image at
    ``image_path``.  A color source is used only when reachable; the CLI's
    primary source is an image.
    """
    parsed = parse_projection_mode(mode)
    concrete_threshold = validate_threshold(threshold)
    if parsed is ProjectionMode.DARK:
        return ModeName.DARK
    if parsed is ProjectionMode.LIGHT:
        return ModeName.LIGHT

    if seed_color is not None:
        luminance = relative_luminance_from_hex(seed_color)
    elif image_path is not None:
        luminance = image_mean_luminance(image_path)
    else:
        raise SmartModeError("smart projection mode requires an image or seed color")
    return resolve_smart_mode(luminance, concrete_threshold)
