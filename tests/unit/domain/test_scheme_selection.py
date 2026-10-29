from __future__ import annotations

import pytest

from theme_producer.domain.engines import EngineDefinition, EngineParameterDefinition
from theme_producer.domain.exceptions import InvalidSchemeTypeError
from theme_producer.domain.scheme_policy import ImageMetrics, SchemeVariant
from theme_producer.domain.scheme_selection import (
    SMART_SCHEME_TYPE,
    SchemeResolution,
    engine_scheme_default,
    is_smart_scheme_type,
    normalize_scheme_type,
    resolve_requested_scheme_type,
)


@pytest.mark.parametrize("variant", [variant.value for variant in SchemeVariant])
def test_concrete_variants_are_accepted(variant: str) -> None:
    assert normalize_scheme_type(variant) == variant


def test_smart_pseudo_value_is_accepted() -> None:
    assert normalize_scheme_type(" scheme-smart ") == SMART_SCHEME_TYPE
    assert is_smart_scheme_type("scheme-smart") is True
    assert is_smart_scheme_type("scheme-smart ") is True
    assert is_smart_scheme_type("scheme-vibrant") is False


@pytest.mark.parametrize("value", ["", "  ", "scheme-nope", None, 42])
def test_unknown_or_empty_values_raise_the_typed_error(value: object) -> None:
    with pytest.raises(InvalidSchemeTypeError):
        normalize_scheme_type(value)


def test_precedence_is_param_then_settings_then_engine_default() -> None:
    assert (
        resolve_requested_scheme_type("scheme-content", "scheme-vibrant", "scheme-neutral")
        == "scheme-content"
    )
    assert (
        resolve_requested_scheme_type(None, "scheme-vibrant", "scheme-neutral") == "scheme-vibrant"
    )
    assert resolve_requested_scheme_type(None, None, "scheme-neutral") == "scheme-neutral"
    assert resolve_requested_scheme_type(None, None, None) == "scheme-tonal-spot"


def test_engine_default_reads_the_catalog_parameter() -> None:
    definition = EngineDefinition(
        name="demo",
        display_name="Demo",
        description="",
        min_version="1",
        parameters=(
            EngineParameterDefinition(
                name="scheme_type", param_type="str", default="scheme-neutral"
            ),
        ),
    )

    assert engine_scheme_default(definition) == "scheme-neutral"


def test_engine_default_falls_back_when_the_catalog_has_no_scheme_type() -> None:
    definition = EngineDefinition(
        name="demo",
        display_name="Demo",
        description="",
        min_version="1",
        parameters=(),
    )

    assert engine_scheme_default(definition) == "scheme-tonal-spot"


def test_resolution_to_dict_carries_metrics_and_profile() -> None:
    metrics = ImageMetrics(
        saturation=1.0,
        colorfulness=0.3,
        lightness=0.2,
        contrast=0.1,
        hue_diversity=0.0,
    )
    resolution = SchemeResolution(
        requested="scheme-smart",
        variant=SchemeVariant.VIBRANT,
        profile="balanced",
        metrics=metrics,
        catalog_path="/policies.yaml",
    )

    payload = resolution.to_dict()
    assert payload["smart"] is True
    assert payload["variant"] == "scheme-vibrant"
    assert payload["profile"] == "balanced"
    assert payload["catalog_path"] == "/policies.yaml"
    assert payload["metrics"] == {
        "saturation": 1.0,
        "colorfulness": 0.3,
        "lightness": 0.2,
        "contrast": 0.1,
        "hue_diversity": 0.0,
    }


def test_explicit_resolution_has_no_policy_side_data() -> None:
    resolution = SchemeResolution(requested="scheme-content", variant=SchemeVariant.CONTENT)

    assert resolution.smart is False
    assert resolution.to_dict()["metrics"] is None
    assert resolution.to_dict()["profile"] is None
