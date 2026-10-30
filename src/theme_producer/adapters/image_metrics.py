"""Measure normalized scheme-policy metrics from an image or seed color.

The adapter implements :class:`~theme_producer.ports.image_metrics.ImageMetricsPort`
for the ``scheme-smart`` policy described in ``docs/SCHEME-POLICY.md``. It is
deterministic and does no caching: every call decodes the source afresh.

Pillow pipeline
---------------
For an ``image`` request::

    Image.open(path).convert("RGB").resize((256, 256), <triangle kernel>)

Alpha is dropped by ``convert("RGB")`` and the 256x256 Triangle resize makes the
result independent of the source dimensions. Pillow exposes its triangle
interpolation kernel as ``Resampling.BILINEAR``; a build that provides
``Resampling.TRIANGLE`` is honored instead. The five metrics are then computed
over the 65,536 resulting pixels (8-bit sRGB).

Formulas
--------
Let ``R, G, B`` be the 8-bit channel values in ``[0, 255]`` and ``r, g, b`` the
same channels in ``[0, 1]`` (``byte / 255``).

* **saturation** — mean HSV saturation::

      s = (max(r, g, b) - min(r, g, b)) / max(r, g, b)   (0 when max = 0)
      saturation = mean(s)

* **lightness** — mean relative luminance with the sRGB transfer function and
  Rec.709 coefficients::

      lin(c) = c / 12.92                        if c <= 0.04045
      lin(c) = ((c + 0.055) / 1.055) ** 2.4     otherwise
      L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
      lightness = mean(L)

* **contrast** — population standard deviation of ``L``, normalized by the
  largest possible standard deviation of a ``[0, 1]`` population, which is
  ``0.5`` (a 50/50 split between 0 and 1)::

      contrast = min(1, population_stddev(L) / 0.5)

* **colorfulness** — Hasler-Süsstrunk, computed in 8-bit channel units::

      rg = R - G
      yb = 0.5 * (R + G) - B
      M = sqrt(var(rg) + var(yb)) + 0.3 * sqrt(mean(rg) ** 2 + mean(yb) ** 2)
      colorfulness = min(1, M / 255)

  ``var`` is the population variance. The divisor ``255`` is one full 8-bit
  channel step, so a mean/std-dev of one channel unit contributes ``1``. ``M``
  can theoretically reach ``255 * (1 + 0.3) * sqrt(2) ~= 468.8`` for
  pathological images; the final clamp keeps the domain invariant ``[0, 1]``.

* **hue_diversity** — saturation-weighted circular variance of hue. With
  ``theta = 2 * pi * h`` from HSV, weights ``w = s``, and total weight
  ``W = sum(w)``::

      C = sum(w * cos(theta)) / W
      S = sum(w * sin(theta)) / W
      hue_diversity = 1 - sqrt(C ** 2 + S ** 2)       (0 when W = 0)

  The result is already in ``[0, 1]``: one hue gives ``0``, an even spread over
  the hue circle approaches ``1``. The final value is clamped for float safety.

Color source
------------
A ``color`` request has no image. Its metrics come from the single seed color:
``saturation`` and ``lightness`` use the formulas above on that one pixel;
``colorfulness``, ``contrast`` and ``hue_diversity`` are ``0`` because there is
no population to vary over.

A ``json`` request has no measurable source and is rejected with
:class:`~theme_producer.domain.exceptions.InvalidImageMetricsError`, as is an
image that Pillow cannot decode.
"""

from __future__ import annotations

import math
from colorsys import rgb_to_hsv
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from theme_producer.domain.color_metrics import (
    relative_luminance_rgb as _relative_luminance,
)
from theme_producer.domain.engines import ThemeRequest
from theme_producer.domain.enums import SourceKind
from theme_producer.domain.exceptions import InvalidImageMetricsError
from theme_producer.domain.models import Color
from theme_producer.domain.scheme_policy import ImageMetrics

__all__ = ["PillowImageMetrics", "measure_top_band_luminance"]

#: The documented resize target (AD-2).
METRICS_SIZE = (256, 256)
#: Pillow's triangle kernel is exposed as ``BILINEAR`` (a linear interpolation
#: with a triangle filter); honor ``TRIANGLE`` if a Pillow build provides it.
_RESAMPLING = getattr(Image.Resampling, "TRIANGLE", Image.Resampling.BILINEAR)

#: The wallpaper bar band: the top 48 rows (or the whole image when shorter).
TOP_BAND_ROWS = 48
#: The band is resized to at most this many pixels wide before averaging.
TOP_BAND_MAX_WIDTH = 64

#: Largest possible population standard deviation of values in [0, 1].
_CONTRAST_DIVISOR = 0.5
#: One full 8-bit channel step; see the module docstring.
_COLORFULNESS_DIVISOR = 255.0


def _clamp_unit(value: float) -> float:
    if not math.isfinite(value):
        raise InvalidImageMetricsError(f"image metric must be finite; got {value!r}")
    return min(1.0, max(0.0, value))


def measure_top_band_luminance(path: Path | str) -> float:
    """Mean WCAG relative luminance of an image's top band.

    The band is the top ``min(48, height)`` rows, resized to at most 64 pixels
    wide (and never taller than 64) before averaging. This is the same signal
    the dotfiles runtime icon-contrast sampler used for its bar band, so
    ``on_backdrop`` answers the question the guard used to answer.

    Raises :class:`InvalidImageMetricsError` when Pillow cannot decode the
    source. Callers that treat the role as best effort catch it and keep the
    ``on_surface`` fallback.
    """
    image_path = Path(path)
    try:
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            band = rgb.crop((0, 0, width, min(TOP_BAND_ROWS, height)))
            band_width, band_height = band.size
            thumb = band.resize(
                (
                    max(1, min(band_width, TOP_BAND_MAX_WIDTH)),
                    max(1, min(band_height, TOP_BAND_MAX_WIDTH)),
                )
            )
            pixels = list(thumb.getdata())
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise InvalidImageMetricsError(
            f"cannot decode image for on_backdrop: {image_path}: {exc}"
        ) from exc

    if not pixels:  # pragma: no cover - a decoded Pillow image always has pixels
        raise InvalidImageMetricsError(f"image has no pixels: {image_path}")
    total = sum(_relative_luminance(r, g, b) for r, g, b in pixels)
    return total / len(pixels)


class PillowImageMetrics:
    """Pillow-backed :class:`ImageMetricsPort` implementation."""

    def measure(self, request: ThemeRequest) -> ImageMetrics:
        """Return normalized metrics for the request's single source."""
        if not isinstance(request, ThemeRequest):
            raise InvalidImageMetricsError(f"image metrics require a ThemeRequest; got {request!r}")

        kind = SourceKind(request.source_kind)
        if kind is SourceKind.JSON:
            raise InvalidImageMetricsError(
                "a json request has no measurable source for scheme metrics; "
                "use an image or a seed color"
            )
        if kind is SourceKind.COLOR:
            if request.color is None:  # ThemeRequest guarantees this; keep the type narrow
                raise InvalidImageMetricsError("color request is missing its seed color")
            return self._measure_color(request.color)
        if request.image_path is None:  # ThemeRequest guarantees this; keep the type narrow
            raise InvalidImageMetricsError("image request is missing its image path")
        return self._measure_image(Path(request.image_path))

    def _measure_image(self, path: Path) -> ImageMetrics:
        try:
            with Image.open(path) as image:
                rgb_image = image.convert("RGB").resize(METRICS_SIZE, _RESAMPLING)
                pixels = list(rgb_image.getdata())
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
            raise InvalidImageMetricsError(
                f"cannot decode image for scheme metrics: {path}: {exc}"
            ) from exc

        count = len(pixels)
        if not count:  # pragma: no cover - a decoded Pillow image always has pixels
            raise InvalidImageMetricsError(f"image has no pixels: {path}")

        saturation_total = 0.0
        # Welford accumulators: stable population variance, exactly zero for a
        # constant population (a solid color).
        luminance_mean = 0.0
        luminance_m2 = 0.0
        rg_mean = 0.0
        rg_m2 = 0.0
        yb_mean = 0.0
        yb_m2 = 0.0
        hue_cosine_total = 0.0
        hue_sine_total = 0.0
        hue_weight_total = 0.0

        for index, (r, g, b) in enumerate(pixels, start=1):
            hue, saturation, _value = rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            saturation_total += saturation

            luminance = _relative_luminance(r, g, b)
            luminance_delta = luminance - luminance_mean
            luminance_mean += luminance_delta / index
            luminance_m2 += luminance_delta * (luminance - luminance_mean)

            rg = r - g
            rg_delta = rg - rg_mean
            rg_mean += rg_delta / index
            rg_m2 += rg_delta * (rg - rg_mean)

            yb = 0.5 * (r + g) - b
            yb_delta = yb - yb_mean
            yb_mean += yb_delta / index
            yb_m2 += yb_delta * (yb - yb_mean)

            if saturation > 0.0:
                angle = 2.0 * math.pi * hue
                hue_cosine_total += saturation * math.cos(angle)
                hue_sine_total += saturation * math.sin(angle)
                hue_weight_total += saturation

        saturation = saturation_total / count
        lightness = luminance_mean
        contrast = _clamp_unit(math.sqrt(luminance_m2 / count) / _CONTRAST_DIVISOR)

        rg_stddev = math.sqrt(rg_m2 / count)
        yb_stddev = math.sqrt(yb_m2 / count)
        colorfulness_value = math.hypot(rg_stddev, yb_stddev) + 0.3 * math.hypot(rg_mean, yb_mean)
        colorfulness = _clamp_unit(colorfulness_value / _COLORFULNESS_DIVISOR)

        if hue_weight_total > 0.0:
            mean_cosine = hue_cosine_total / hue_weight_total
            mean_sine = hue_sine_total / hue_weight_total
            hue_diversity = _clamp_unit(1.0 - math.hypot(mean_cosine, mean_sine))
        else:
            hue_diversity = 0.0

        return ImageMetrics(
            saturation=_clamp_unit(saturation),
            colorfulness=colorfulness,
            lightness=_clamp_unit(lightness),
            contrast=contrast,
            hue_diversity=hue_diversity,
        )

    def _measure_color(self, value: str) -> ImageMetrics:
        try:
            rgb = Color.from_hex(value).rgb
        except ValueError as exc:  # ThemeValidationError from Color.from_hex
            raise InvalidImageMetricsError(
                f"invalid seed color for scheme metrics: {value!r}"
            ) from exc

        assert rgb is not None  # Color.from_hex always derives rgb
        r, g, b = rgb
        _hue, saturation, _value = rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return ImageMetrics(
            saturation=_clamp_unit(saturation),
            colorfulness=0.0,
            lightness=_clamp_unit(_relative_luminance(r, g, b)),
            contrast=0.0,
            hue_diversity=0.0,
        )
