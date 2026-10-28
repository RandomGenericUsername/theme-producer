"""Image-metrics port.

Protocol only: this module names the boundary and does not measure anything.
An adapter (``PillowImageMetrics`` in a later ticket) decodes the source,
normalizes it per ``docs/SCHEME-POLICY.md``, and returns :class:`ImageMetrics`.
Adapters may raise :class:`~theme_producer.domain.exceptions.SchemePolicyError`
subclasses for an undecodable or unsupported source.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from theme_producer.domain.engines import ThemeRequest
from theme_producer.domain.scheme_policy import ImageMetrics

__all__ = ["ImageMetricsPort"]


@runtime_checkable
class ImageMetricsPort(Protocol):
    """Measure normalized metrics from a request's single source."""

    def measure(self, request: ThemeRequest) -> ImageMetrics:
        """Return metrics for ``request``.

        An ``image`` request is decoded and measured on the documented
        resize. A ``color`` request derives the metrics from that single color
        (``contrast``, ``hue_diversity`` and ``colorfulness`` are ``0``). A
        ``json`` request has no measurable source; adapters reject it with a
        typed scheme-policy error.
        """
        ...
