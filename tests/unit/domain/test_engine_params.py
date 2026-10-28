from __future__ import annotations

from pathlib import Path

import pytest

from theme_producer.domain.engine_params import ParameterResolutionService
from theme_producer.domain.engines import (
    EngineConfig,
    EngineParameterDefinition,
    ThemeRequest,
)
from theme_producer.domain.enums import SourceKind
from theme_producer.domain.exceptions import EngineConfigError, ThemeValidationError

PARAMETERS = (
    EngineParameterDefinition(
        name="mode",
        param_type="str",
        default="dark",
        choices=("dark", "light", "smart"),
        description="mode",
    ),
    EngineParameterDefinition(
        name="contrast",
        param_type="float",
        default=0.0,
        description="contrast",
    ),
    EngineParameterDefinition(
        name="source_color_index",
        param_type="int",
        default=0,
        description="index",
    ),
)


def test_defaults_are_resolved_in_catalog_order() -> None:
    resolved = ParameterResolutionService.resolve_all(PARAMETERS, {})

    assert resolved == {"mode": "dark", "contrast": 0.0, "source_color_index": 0}
    assert list(resolved) == ["mode", "contrast", "source_color_index"]


def test_override_wins_and_is_typed() -> None:
    resolved = ParameterResolutionService.resolve_all(
        PARAMETERS,
        {"mode": "light", "contrast": "0.5", "source_color_index": "2"},
    )

    assert resolved == {"mode": "light", "contrast": 0.5, "source_color_index": 2}
    assert isinstance(resolved["contrast"], float)
    assert isinstance(resolved["source_color_index"], int)


def test_invalid_choice_raises_engine_config_error() -> None:
    with pytest.raises(EngineConfigError, match="invalid choice"):
        ParameterResolutionService.resolve_all(PARAMETERS, {"mode": "sepia"})


def test_missing_required_parameter_raises() -> None:
    required = (
        EngineParameterDefinition(
            name="seed",
            param_type="str",
            default=None,
            choices=None,
            description="",
            required=True,
        ),
    )

    with pytest.raises(EngineConfigError, match="required parameter"):
        ParameterResolutionService.resolve_all(required, {})

    assert ParameterResolutionService.resolve_all(required, {"seed": "x"}) == {"seed": "x"}


def test_unknown_override_raises() -> None:
    with pytest.raises(EngineConfigError, match="unknown parameter"):
        ParameterResolutionService.resolve_all(PARAMETERS, {"mystery": 1})


def test_invalid_type_raises() -> None:
    with pytest.raises(EngineConfigError, match="expected an int"):
        ParameterResolutionService.resolve_all(PARAMETERS, {"source_color_index": True})


def test_theme_request_accepts_exactly_one_matching_source(tmp_path: Path) -> None:
    request = ThemeRequest(source_kind="image", image_path=tmp_path / "wall.png")

    assert request.source_kind is SourceKind.IMAGE
    assert request.image_path == tmp_path / "wall.png"


def test_theme_request_rejects_zero_or_multiple_sources() -> None:
    with pytest.raises(ThemeValidationError, match="exactly one source"):
        ThemeRequest(source_kind="color")
    with pytest.raises(ThemeValidationError, match="exactly one source"):
        ThemeRequest(source_kind="image", image_path=Path("a.png"), color="#000000")


def test_theme_request_rejects_kind_mismatch() -> None:
    with pytest.raises(ThemeValidationError, match="requires 'image_path'"):
        ThemeRequest(source_kind="image", color="#000000")


def test_engine_config_freezes_params_and_validates_timeout() -> None:
    params = {"mode": "dark"}
    config = EngineConfig(engine="matugen", params=params, timeout=30)
    params["mode"] = "light"

    assert config.params["mode"] == "dark"
    with pytest.raises(EngineConfigError):
        EngineConfig(engine="matugen", params={}, timeout="soon")  # type: ignore[arg-type]
