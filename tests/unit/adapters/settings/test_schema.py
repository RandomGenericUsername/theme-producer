from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from theme_producer.adapters.settings.schema import (
    ContainerSettingsSchema,
    CoreSettingsSchema,
    GenerationSettingsSchema,
    OutputSettingsSchema,
    RuntimeSettingsSchema,
    TemplatesSettingsSchema,
)


class TestCoreSettingsSchema:
    def test_valid_full_config(self) -> None:
        data = {
            "output": {
                "directory": "/tmp/out",
                "default_formats": ["json"],
                "overwrite": True,
                "verbosity": 2,
                "apply_to_terminal": False,
                "default_mode": "smart",
                "smart_threshold": 0.7,
            },
            "generation": {"engine": "matugen", "default_params": {"quality": "high"}},
            "templates": {"directory": "/tmp/templates"},
            "runtime": {"mode": "local"},
            "container": {
                "engine": "docker",
                "image_prefix": "myapp",
                "image_tag": "v1",
                "timeout_seconds": 600,
                "memory_limit": "2G",
            },
        }
        schema = CoreSettingsSchema.model_validate(data)

        assert schema.output.directory == Path("/tmp/out")
        assert schema.output.default_formats == ["json"]
        assert schema.output.verbosity == 2
        assert schema.output.apply_to_terminal is False
        assert schema.output.default_mode == "smart"
        assert schema.output.smart_threshold == 0.7
        assert schema.generation.engine == "matugen"
        assert schema.generation.default_params == {"quality": "high"}
        assert schema.generation.scheme_type == "scheme-tonal-spot"
        assert schema.generation.scheme_policy == "balanced"
        assert schema.templates.directory == "/tmp/templates"
        assert schema.runtime.mode == "local"
        assert schema.container.engine == "docker"
        assert schema.container.image_prefix == "myapp"
        assert schema.container.image_tag == "v1"
        assert schema.container.timeout_seconds == 600
        assert schema.container.memory_limit == "2g"

    def test_minimal_config_with_defaults(self) -> None:
        schema = CoreSettingsSchema.model_validate({"output": {"directory": "/out"}})

        assert schema.output.default_formats == []
        assert schema.output.overwrite is False
        assert schema.output.verbosity == 1
        assert schema.output.apply_to_terminal is True
        assert schema.output.default_mode == "dark"
        assert schema.output.smart_threshold == 0.5
        assert schema.generation.engine == "matugen"
        assert schema.generation.default_params == {}
        assert schema.generation.scheme_type == "scheme-tonal-spot"
        assert schema.generation.scheme_policy == "balanced"
        assert schema.templates.directory == ""
        assert schema.runtime.mode == "local"
        assert schema.container.engine == "podman"
        assert schema.container.image_prefix == "tpr"
        assert schema.container.image_tag == ""
        assert schema.container.timeout_seconds == 300
        assert schema.container.memory_limit == "512m"

    def test_missing_output_raises(self) -> None:
        with pytest.raises(ValidationError):
            CoreSettingsSchema.model_validate({})


class TestOutputSettingsSchema:
    def test_empty_directory_rejected(self) -> None:
        with pytest.raises(ValidationError, match="directory must not be empty"):
            OutputSettingsSchema(directory="  ")

    @pytest.mark.parametrize("verbosity", [0, 1, 2, 3])
    def test_verbosity_range_accepted(self, verbosity: int) -> None:
        assert OutputSettingsSchema(directory="/out", verbosity=verbosity).verbosity == verbosity

    @pytest.mark.parametrize("verbosity", [-1, 4])
    def test_verbosity_out_of_range_rejected(self, verbosity: int) -> None:
        with pytest.raises(ValidationError):
            OutputSettingsSchema(directory="/out", verbosity=verbosity)

    @pytest.mark.parametrize("mode", ["dark", "light", "smart", " SMART "])
    def test_default_mode_accepts_projection_modes(self, mode: str) -> None:
        assert OutputSettingsSchema(directory="/out", default_mode=mode).default_mode == (
            mode.strip().lower()
        )

    def test_invalid_default_mode_raises_clear_message(self) -> None:
        with pytest.raises(ValidationError, match="Invalid output default mode 'sepia'"):
            OutputSettingsSchema(directory="/out", default_mode="sepia")

    @pytest.mark.parametrize("value", [0.0, 0.5, 1.0, "0.25"])
    def test_smart_threshold_accepts_range(self, value: object) -> None:
        assert OutputSettingsSchema(directory="/out", smart_threshold=value).smart_threshold == (
            float(value)  # type: ignore[arg-type]
        )

    @pytest.mark.parametrize("value", [-0.1, 1.1, "nan", "inf"])
    def test_smart_threshold_rejects_out_of_range(self, value: object) -> None:
        with pytest.raises(ValidationError, match=r"smart threshold must be a number in \[0, 1\]"):
            OutputSettingsSchema(directory="/out", smart_threshold=value)


class TestGenerationSettingsSchema:
    def test_default_engine(self) -> None:
        assert GenerationSettingsSchema().engine == "matugen"

    def test_empty_engine_rejected(self) -> None:
        with pytest.raises(ValidationError, match="engine must not be empty"):
            GenerationSettingsSchema(engine="  ")

    def test_default_params_accepts_arbitrary_values(self) -> None:
        schema = GenerationSettingsSchema(default_params={"contrast": 0.5, "scheme_type": "tonal"})
        assert schema.default_params == {"contrast": 0.5, "scheme_type": "tonal"}

    def test_default_scheme_type_is_tonal_spot(self) -> None:
        assert GenerationSettingsSchema().scheme_type == "scheme-tonal-spot"

    @pytest.mark.parametrize(
        "scheme_type",
        ["scheme-smart", "scheme-content", "scheme-vibrant", "scheme-monochrome"],
    )
    def test_real_variants_and_smart_are_accepted(self, scheme_type: str) -> None:
        assert GenerationSettingsSchema(scheme_type=scheme_type).scheme_type == scheme_type

    def test_unknown_scheme_type_rejected(self) -> None:
        with pytest.raises(ValidationError, match="unknown scheme_type 'scheme-rainbow-2'"):
            GenerationSettingsSchema(scheme_type="scheme-rainbow-2")

    def test_empty_scheme_type_rejected(self) -> None:
        with pytest.raises(ValidationError, match="scheme_type must be a non-empty"):
            GenerationSettingsSchema(scheme_type="  ")

    def test_default_scheme_policy_is_balanced(self) -> None:
        assert GenerationSettingsSchema().scheme_policy == "balanced"

    def test_named_scheme_policy_is_kept(self) -> None:
        assert GenerationSettingsSchema(scheme_policy="vivid").scheme_policy == "vivid"

    def test_empty_scheme_policy_rejected(self) -> None:
        with pytest.raises(ValidationError, match="scheme_policy must be a non-empty"):
            GenerationSettingsSchema(scheme_policy="  ")


class TestTemplatesSettingsSchema:
    def test_default_directory_is_empty(self) -> None:
        assert TemplatesSettingsSchema().directory == ""


class TestRuntimeSettingsSchema:
    def test_valid_local(self) -> None:
        assert RuntimeSettingsSchema(mode="local").mode == "local"

    def test_valid_container(self) -> None:
        assert RuntimeSettingsSchema(mode="container").mode == "container"

    def test_invalid_mode_raises_clear_message(self) -> None:
        with pytest.raises(ValidationError, match="Invalid runtime mode 'hybrid'"):
            RuntimeSettingsSchema(mode="hybrid")


class TestContainerSettingsSchema:
    def test_valid_engines(self) -> None:
        assert ContainerSettingsSchema(engine="docker").engine == "docker"
        assert ContainerSettingsSchema(engine="podman").engine == "podman"

    def test_invalid_engine_raises_clear_message(self) -> None:
        with pytest.raises(ValidationError, match="Invalid container engine 'containerd'"):
            ContainerSettingsSchema(engine="containerd")

    @pytest.mark.parametrize("value", ["512m", "2G", "128", "1t"])
    def test_memory_limit_accepts_valid_shapes(self, value: str) -> None:
        assert ContainerSettingsSchema(memory_limit=value).memory_limit == value.lower()

    @pytest.mark.parametrize("value", ["abc", "512mb", "", "-1g"])
    def test_memory_limit_rejects_invalid_shapes(self, value: str) -> None:
        with pytest.raises(ValidationError, match="Invalid memory limit"):
            ContainerSettingsSchema(memory_limit=value)

    def test_empty_image_tag_is_accepted(self) -> None:
        assert ContainerSettingsSchema(image_tag="").image_tag == ""

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Timeout must be non-negative"):
            ContainerSettingsSchema(timeout_seconds=-1)

    def test_zero_timeout_accepted(self) -> None:
        assert ContainerSettingsSchema(timeout_seconds=0).timeout_seconds == 0
