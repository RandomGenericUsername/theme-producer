from __future__ import annotations

import logging
from pathlib import Path

import pytest

from theme_producer.adapters.engines_catalog_loader import YamlEngineCatalogLoader
from theme_producer.domain.exceptions import EngineConfigError

CATALOG = """
matugen:
  display_name: Custom Matugen
  description: "custom catalog"
  min_version: "9.9.9"
  parameters:
    - name: mode
      param_type: str
      default: light
      choices: [light, dark]
"""


def _write_catalog(tmp_path: Path, text: str = CATALOG) -> Path:
    path = tmp_path / "engines.yaml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_catalog_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep host engine-catalog env out of the default-path tests."""
    monkeypatch.delenv("THEME_ENGINES_CONFIG_FILE_PATH", raising=False)


def test_default_catalog_loads_matugen_and_native() -> None:
    catalog = YamlEngineCatalogLoader().load()

    assert set(catalog) == {"matugen", "native"}
    matugen = catalog["matugen"]
    assert matugen.name == "matugen"
    assert matugen.display_name == "Matugen"
    assert matugen.min_version == "4.2.0"
    assert [param.name for param in matugen.parameters] == [
        "mode",
        "scheme_type",
        "contrast",
        "source_color_index",
        "timeout",
        "fallback_color",
    ]
    assert {param.name: param.default for param in matugen.parameters} == {
        "mode": "dark",
        "scheme_type": "scheme-tonal-spot",
        "contrast": 0.0,
        "source_color_index": 0,
        "timeout": 300,
        "fallback_color": "",
    }
    assert matugen.parameters[0].choices == ("dark", "light", "smart")
    matugen_schemes = matugen.parameters[1].choices
    assert len(matugen_schemes) == 10
    assert "scheme-smart" in matugen_schemes
    native = catalog["native"]
    assert native.display_name == "Native"
    assert native.min_version == "0.1.0"
    native_schemes = native.parameters[1].choices
    assert len(native_schemes) == 9
    assert "scheme-smart" not in native_schemes


def test_explicit_path_wins(tmp_path: Path) -> None:
    path = _write_catalog(tmp_path)

    catalog = YamlEngineCatalogLoader().load(explicit_path=str(path))

    assert catalog["matugen"].display_name == "Custom Matugen"
    assert catalog["matugen"].min_version == "9.9.9"
    assert catalog["matugen"].parameters[0].default == "light"


def test_env_path_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write_catalog(tmp_path)
    monkeypatch.setenv("THEME_ENGINES_CONFIG_FILE_PATH", str(path))

    catalog = YamlEngineCatalogLoader().load()

    assert catalog["matugen"].display_name == "Custom Matugen"


def test_invalid_yaml_raises_typed_error(tmp_path: Path) -> None:
    path = _write_catalog(tmp_path, "matugen: [\n")

    with pytest.raises(EngineConfigError, match="engines.yaml"):
        YamlEngineCatalogLoader().load(explicit_path=str(path))


def test_invalid_param_type_raises_typed_error(tmp_path: Path) -> None:
    path = _write_catalog(
        tmp_path,
        """
matugen:
  parameters:
    - name: mode
      param_type: colour
      default: dark
""",
    )

    with pytest.raises(EngineConfigError):
        YamlEngineCatalogLoader().load(explicit_path=str(path))


def test_unknown_engine_is_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = _write_catalog(
        tmp_path,
        """
mystery:
  display_name: Mystery
  parameters: []
""",
    )

    with caplog.at_level(logging.WARNING):
        catalog = YamlEngineCatalogLoader().load(explicit_path=str(path))

    assert catalog == {}
    assert "Unknown engine 'mystery'" in caplog.text
