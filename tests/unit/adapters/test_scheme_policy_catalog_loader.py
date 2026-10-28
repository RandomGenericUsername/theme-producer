from __future__ import annotations

from pathlib import Path
from unittest.mock import create_autospec

import pytest
from config_assembler_engine.application.use_cases import AssembleConfiguration
from config_assembler_engine.domain.models import (
    AssemblyResult,
    PathSource,
    ResolvedPath,
)

from theme_producer.adapters.schemas.scheme_policies_catalog_schema import (
    SchemePolicyCatalogSchema,
)
from theme_producer.adapters.scheme_policy_catalog_loader import (
    YamlSchemePolicyCatalogLoader,
)
from theme_producer.domain.exceptions import (
    InvalidSchemePolicyCatalogError,
    InvalidSchemeRuleError,
    UnknownSchemePolicyError,
)
from theme_producer.domain.scheme_policy import Operator, SchemeVariant

MINIMAL = """
version: 1
default: custom
policies:
  custom:
    default: scheme-neutral
    rules:
      - when: { contrast: { gte: 0.4 } }
        variant: scheme-vibrant
"""


def _write(tmp_path: Path, text: str = MINIMAL, name: str = "custom-policies.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_packaged_catalog_loads_all_documented_profiles() -> None:
    loader = YamlSchemePolicyCatalogLoader()

    catalog = loader.load()

    assert catalog.version == 1
    assert catalog.default_policy == "balanced"
    assert set(catalog.policies) == {"balanced", "vivid", "muted", "source-faithful"}
    assert catalog.policies["balanced"].default is SchemeVariant.TONAL_SPOT
    assert [rule.variant for rule in catalog.policies["balanced"].rules] == [
        SchemeVariant.MONOCHROME,
        SchemeVariant.NEUTRAL,
        SchemeVariant.VIBRANT,
        SchemeVariant.EXPRESSIVE,
    ]
    assert catalog.policies["vivid"].default is SchemeVariant.VIBRANT
    assert catalog.policies["muted"].default is SchemeVariant.NEUTRAL
    assert catalog.policies["source-faithful"].default is SchemeVariant.CONTENT
    assert loader.last_source_path is not None
    assert loader.last_source_path.name == "scheme-policies.yaml"
    assert loader.last_source_path.parent.name == "defaults"


def test_explicit_path_is_used(tmp_path: Path) -> None:
    path = _write(tmp_path)
    loader = YamlSchemePolicyCatalogLoader()

    catalog = loader.load(explicit_path=str(path))

    assert catalog.default_policy == "custom"
    assert catalog.policies["custom"].rules[0].variant is SchemeVariant.VIBRANT
    assert loader.last_source_path == path.resolve()


def test_env_path_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write(tmp_path)
    monkeypatch.setenv("THEME_SCHEME_POLICIES_CONFIG_FILE_PATH", str(path))

    catalog = YamlSchemePolicyCatalogLoader().load()

    assert catalog.default_policy == "custom"


def test_explicit_path_beats_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write(
        tmp_path,
        MINIMAL.replace("default: custom", "default: from-env").replace("  custom:", "  from-env:"),
        name="env-policies.yaml",
    )
    explicit_path = _write(tmp_path)
    monkeypatch.setenv("THEME_SCHEME_POLICIES_CONFIG_FILE_PATH", str(env_path))

    catalog = YamlSchemePolicyCatalogLoader().load(explicit_path=str(explicit_path))

    assert catalog.default_policy == "custom"


def test_xdg_catalog_is_used_when_no_explicit_or_env_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    xdg = tmp_path / "xdg"
    target = xdg / "theme-producer" / "scheme-policies.yaml"
    target.parent.mkdir(parents=True)
    target.write_text(MINIMAL, encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))

    catalog = YamlSchemePolicyCatalogLoader().load()

    assert catalog.default_policy == "custom"


def test_directory_traversal_finds_a_catalog_up_to_three_levels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog_path = tmp_path / "scheme-policies.yaml"
    catalog_path.write_text(MINIMAL, encoding="utf-8")
    work = tmp_path / "a" / "b" / "c"
    work.mkdir(parents=True)
    monkeypatch.chdir(work)

    catalog = YamlSchemePolicyCatalogLoader().load()

    assert catalog.default_policy == "custom"


def test_between_operator_is_supported(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
default: ranged
policies:
  ranged:
    default: scheme-neutral
    rules:
      - when: { contrast: { between: [0.2, 0.4] } }
        variant: scheme-fidelity
""",
    )

    catalog = YamlSchemePolicyCatalogLoader().load(explicit_path=str(path))
    condition = catalog.policies["ranged"].rules[0].conditions[0]

    assert condition.operator is Operator.BETWEEN
    assert condition.value == 0.2
    assert condition.upper == 0.4


def test_between_accepts_min_max_mapping(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
default: ranged
policies:
  ranged:
    default: scheme-neutral
    rules:
      - when: { contrast: { between: { min: 0.2, max: 0.4 } } }
        variant: scheme-fidelity
""",
    )

    catalog = YamlSchemePolicyCatalogLoader().load(explicit_path=str(path))
    condition = catalog.policies["ranged"].rules[0].conditions[0]

    assert condition.operator is Operator.BETWEEN
    assert (condition.value, condition.upper) == (0.2, 0.4)


def test_invalid_between_operand_is_typed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
default: bad
policies:
  bad:
    default: scheme-neutral
    rules:
      - when: { contrast: { between: 0.4 } }
        variant: scheme-vibrant
""",
    )

    with pytest.raises(InvalidSchemeRuleError, match="between"):
        YamlSchemePolicyCatalogLoader().load(explicit_path=str(path))


def test_invalid_yaml_is_reported_with_the_source_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "version: 1\npolicies: [\n")

    with pytest.raises(InvalidSchemePolicyCatalogError) as excinfo:
        YamlSchemePolicyCatalogLoader().load(explicit_path=str(path))

    assert str(path.resolve()) in str(excinfo.value)


@pytest.mark.parametrize(
    ("body", "error", "match"),
    [
        (
            MINIMAL.replace("default: custom", "default: missing"),
            UnknownSchemePolicyError,
            "default scheme policy",
        ),
        (
            MINIMAL.replace("variant: scheme-vibrant", "variant: scheme-smart"),
            InvalidSchemeRuleError,
            "rule variant",
        ),
        (
            MINIMAL.replace("colorfulness: { gte: 0.4 }", "luminosity: { gte: 0.4 }").replace(
                "contrast:", "luminosity:"
            ),
            InvalidSchemeRuleError,
            "condition metric",
        ),
        (
            MINIMAL.replace("contrast: { gte: 0.4 }", "contrast: { eq: 0.4 }"),
            InvalidSchemeRuleError,
            "condition operator",
        ),
        (
            MINIMAL.replace(
                "    rules:\n"
                "      - when: { contrast: { gte: 0.4 } }\n"
                "        variant: scheme-vibrant\n",
                "    rules: []\n",
            ),
            InvalidSchemeRuleError,
            "at least one rule",
        ),
        (
            MINIMAL.replace("  custom:\n    default: scheme-neutral\n", "  custom:\n"),
            InvalidSchemePolicyCatalogError,
            "default",
        ),
        (
            MINIMAL.replace("version: 1\n", ""),
            InvalidSchemePolicyCatalogError,
            "version",
        ),
        (
            MINIMAL.replace("default: custom\n", ""),
            InvalidSchemePolicyCatalogError,
            "default",
        ),
    ],
)
def test_catalog_shape_and_vocabulary_errors_name_the_source(
    tmp_path: Path, body: str, error: type[Exception], match: str
) -> None:
    path = _write(tmp_path, body)

    with pytest.raises(error, match=match) as excinfo:
        YamlSchemePolicyCatalogLoader().load(explicit_path=str(path))

    assert str(path.resolve()) in str(excinfo.value)


def test_out_of_range_threshold_is_reported_with_the_source_path(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        MINIMAL.replace("gte: 0.4", "gte: 1.4"),
    )

    with pytest.raises(InvalidSchemeRuleError, match="within") as excinfo:
        YamlSchemePolicyCatalogLoader().load(explicit_path=str(path))

    assert str(path.resolve()) in str(excinfo.value)


def test_loader_passes_no_override_rules() -> None:
    mock_assembler = create_autospec(AssembleConfiguration, instance=True)
    mock_assembler.execute.return_value = AssemblyResult(
        config=SchemePolicyCatalogSchema.model_validate_json(
            '{"version": 1, "default": "custom", "policies": {'
            '"custom": {"default": "scheme-neutral", "rules": ['
            '{"when": {"contrast": {"gte": 0.4}}, "variant": "scheme-vibrant"}]}}}'
        ),
        resolved_path=ResolvedPath(Path("/tmp/scheme-policies.yaml"), PathSource.DEFAULT),
        applied_overrides=[],
    )
    loader = YamlSchemePolicyCatalogLoader(assembler=mock_assembler)

    catalog = loader.load()

    assert catalog.default_policy == "custom"
    _, kwargs = mock_assembler.execute.call_args
    assert kwargs["rules"] == []
    assert kwargs["schema"] is SchemePolicyCatalogSchema
    assert kwargs["policy"].env_prefix == "THEME_SCHEME_POLICIES"
