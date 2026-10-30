"""Host-side application of the produced ``on_backdrop`` role.

The engines never write ``on_backdrop``. After an engine returns a Theme, the
processor measures the source image's top band once and applies the pure
selection rule from :mod:`theme_producer.domain.on_backdrop`. Because this step
is shared by both engines, matugen and native produce identical ``on_backdrop``
values for the same image.

No image source (a seed color or an imported JSON theme) keeps the domain
fallback: ``on_backdrop = on_surface``. A source that cannot be decoded also
keeps the fallback; the real engines already fail earlier for an unreadable
image, and this keeps the produced role best effort rather than fatal.
"""

from __future__ import annotations

from pathlib import Path

from theme_producer.adapters.image_metrics import measure_top_band_luminance
from theme_producer.domain.enums import SourceKind
from theme_producer.domain.exceptions import InvalidImageMetricsError
from theme_producer.domain.models import Theme
from theme_producer.domain.on_backdrop import apply_on_backdrop

__all__ = ["theme_with_on_backdrop"]


def theme_with_on_backdrop(theme: Theme, image_path: Path | str | None) -> Theme:
    """Return ``theme`` with both modes' produced role measured from ``image_path``."""
    if image_path is None or theme.source.kind is not SourceKind.IMAGE:
        return theme
    try:
        band_luminance = measure_top_band_luminance(image_path)
    except InvalidImageMetricsError:
        return theme
    return apply_on_backdrop(theme, band_luminance)
