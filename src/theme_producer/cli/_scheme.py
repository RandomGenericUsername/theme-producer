"""Host-side ``scheme-smart`` resolution shared by ``generate`` and ``show``.

The container path never resolves smart itself: the CLI measures the source and
loads the policy catalog on the host, then forwards the concrete variant as a
normal ``--param scheme_type=...``. This module is that single host-side step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from theme_producer.domain.engines import EngineDefinition, ThemeRequest
from theme_producer.domain.exceptions import InvalidSchemeTypeError
from theme_producer.domain.scheme_policy import SchemePolicyCatalog, SchemeVariant
from theme_producer.domain.scheme_policy_resolver import SchemePolicyResolver
from theme_producer.domain.scheme_selection import (
    SchemeResolution,
    engine_scheme_default,
    is_smart_scheme_type,
    resolve_requested_scheme_type,
)
from theme_producer.factory import CliDependencies

__all__ = [
    "apply_scheme_resolution",
    "requested_scheme_type",
    "resolve_scheme",
    "theme_request_for",
]


def theme_request_for(
    image_path: Path,
    *,
    seed_color: str | None = None,
) -> ThemeRequest:
    """Build the single-source request the metrics adapter expects."""
    if seed_color is not None:
        return ThemeRequest(source_kind="color", color=seed_color)
    return ThemeRequest(source_kind="image", image_path=Path(image_path).expanduser())


def requested_scheme_type(
    definition: EngineDefinition,
    settings_scheme_type: str,
    params: dict[str, str],
) -> str:
    """Resolve ``--param`` > ``[generation]`` > catalog default."""
    parameter_value = params["scheme_type"] if "scheme_type" in params else None
    return resolve_requested_scheme_type(
        parameter_value,
        settings_scheme_type,
        engine_scheme_default(definition),
    )


def resolve_scheme(
    deps: CliDependencies,
    *,
    request: ThemeRequest,
    requested: str,
    profile: str | None,
    policies_file: str | None,
) -> SchemeResolution:
    """Return the concrete variant for ``requested``.

    A real variant bypasses the catalog and metrics entirely. Smart loads the
    catalog, selects the profile (the catalog default when ``profile`` is
    ``None``), measures the source, and resolves the first matching rule.
    """
    if not is_smart_scheme_type(requested):
        try:
            variant = SchemeVariant(requested)
        except ValueError as exc:
            raise InvalidSchemeTypeError(f"unknown scheme_type {requested!r}") from exc
        return SchemeResolution(requested=requested, variant=variant)

    loader = deps.scheme_policy_catalog_loader
    catalog: SchemePolicyCatalog = loader.load(policies_file)
    policy = catalog.select(profile)
    metrics = deps.image_metrics.measure(request)
    variant = SchemePolicyResolver.resolve(policy, metrics)
    catalog_path = str(loader.last_source_path) if loader.last_source_path is not None else None
    return SchemeResolution(
        requested=requested,
        variant=variant,
        profile=policy.name,
        metrics=metrics,
        catalog_path=catalog_path,
    )


def apply_scheme_resolution(
    deps: CliDependencies,
    *,
    image_path: Path,
    definition: EngineDefinition,
    settings_scheme_type: str,
    profile: str | None,
    policies_file: str | None,
    params: dict[str, str],
    seed_color: str | None = None,
) -> tuple[SchemeResolution, dict[str, Any]]:
    """Resolve the scheme and return it with concrete engine parameters.

    The returned parameter map always carries a concrete ``scheme_type``, so
    engine choice validation — including native's nine-variant catalog — never
    sees the ``scheme-smart`` pseudo-value.
    """
    requested = requested_scheme_type(definition, settings_scheme_type, params)
    resolution = resolve_scheme(
        deps,
        request=theme_request_for(image_path, seed_color=seed_color),
        requested=requested,
        profile=profile,
        policies_file=policies_file,
    )
    resolved_params = dict(params)
    resolved_params["scheme_type"] = resolution.variant.value
    return resolution, resolved_params
