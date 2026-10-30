"""Pure sRGB luminance and WCAG contrast formulas.

This module is the single source of truth for the transfer function used by
both image measurement (``adapters.image_metrics``) and produced-role selection
(``domain.on_backdrop``). Keeping it in the domain means the formulas have no
I/O and no adapter dependency.

The transfer function is the WCAG 2.1 relative-luminance definition::

    lin(c) = c / 12.92                        if c <= 0.04045
    lin(c) = ((c + 0.055) / 1.055) ** 2.4     otherwise

where ``c`` is an 8-bit channel normalized to ``[0, 1]``. Luminance then uses
the Rec.709 coefficients ``0.2126, 0.7152, 0.0722``.
"""

from __future__ import annotations

from theme_producer.domain.models import Color

__all__ = [
    "REC709_WEIGHTS",
    "contrast_ratio",
    "linearize_byte",
    "relative_luminance",
    "relative_luminance_rgb",
]

#: Rec.709 channel weights for relative luminance.
REC709_WEIGHTS = (0.2126, 0.7152, 0.0722)


def linearize_byte(value: int) -> float:
    """Linearize one 8-bit sRGB channel value."""
    channel = value / 255.0
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


#: Memoized transfer function for every possible 8-bit channel value.
LINEAR_LUT: tuple[float, ...] = tuple(linearize_byte(value) for value in range(256))


def relative_luminance_rgb(r: int, g: int, b: int) -> float:
    """Relative luminance of one 8-bit sRGB pixel."""
    return (
        REC709_WEIGHTS[0] * LINEAR_LUT[r]
        + REC709_WEIGHTS[1] * LINEAR_LUT[g]
        + REC709_WEIGHTS[2] * LINEAR_LUT[b]
    )


def relative_luminance(color: Color) -> float:
    """Relative luminance of a domain :class:`Color`."""
    assert color.rgb is not None  # Color always derives rgb
    r, g, b = color.rgb
    return relative_luminance_rgb(r, g, b)


def contrast_ratio(lum_a: float, lum_b: float) -> float:
    """WCAG contrast ratio ``(L1 + 0.05) / (L2 + 0.05)`` in ``[1, 21]``."""
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)
