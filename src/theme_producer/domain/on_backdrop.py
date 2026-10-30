"""Produced ``on_backdrop`` role: the ink that reads over the wallpaper band.

``on_backdrop`` is not an engine Material role. The engine always emits exactly
the 50 Material roles; ``tpr`` derives this role on the host from the source
image's top band so matugen and native produce the same value for the same
image.

Selection
---------
The candidate set is deliberately neutral-pole only (never a random hue)::

    on_surface, on_surface_variant, on_background, inverse_on_surface,
    inverse_surface, outline, outline_variant, surface, surface_dim,
    surface_container_lowest

The candidate with the highest WCAG contrast ratio against the measured band
luminance wins. Candidates are tried in the tuple order above, so an exact tie
keeps the earlier candidate and ``on_surface`` wins every tie. Selection is
best effort: a theme color cannot beat a pathological band without inventing a
color, so values below the WCAG 4.5 body-text threshold are still returned.

Because the band is measured from the image rather than inferred from the
scheme, ``on_backdrop`` may intentionally sit on the opposite luminance pole
from ``on_surface`` (for example a dark scheme over a bright wallpaper band).
"""

from __future__ import annotations

from dataclasses import replace

from theme_producer.domain.color_metrics import contrast_ratio, relative_luminance
from theme_producer.domain.enums import MaterialRole
from theme_producer.domain.models import Color, Mode, Theme

__all__ = [
    "ON_BACKDROP_CANDIDATES",
    "apply_on_backdrop",
    "select_on_backdrop",
]

#: Neutral-pole candidates, in deterministic tie-breaking order.
ON_BACKDROP_CANDIDATES: tuple[MaterialRole, ...] = (
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


def select_on_backdrop(mode: Mode, band_luminance: float) -> Color:
    """Return the max-contrast neutral candidate for ``band_luminance``.

    Ties keep the earlier candidate, which makes ``on_surface`` the tie winner.
    The result is best effort when every candidate is below WCAG 4.5.
    """
    best = mode.roles[MaterialRole.ON_SURFACE]
    best_ratio = -1.0
    for role in ON_BACKDROP_CANDIDATES:
        candidate = mode.roles[role]
        ratio = contrast_ratio(relative_luminance(candidate), band_luminance)
        if ratio > best_ratio:
            best = candidate
            best_ratio = ratio
    return best


def apply_on_backdrop(theme: Theme, band_luminance: float) -> Theme:
    """Return ``theme`` with both modes' ``on_backdrop`` selected from the band."""
    return replace(
        theme,
        dark=replace(theme.dark, on_backdrop=select_on_backdrop(theme.dark, band_luminance)),
        light=replace(theme.light, on_backdrop=select_on_backdrop(theme.light, band_luminance)),
    )
