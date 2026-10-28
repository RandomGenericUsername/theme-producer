from __future__ import annotations

from pathlib import Path

import pytest

from theme_producer.adapters.jinja_renderer import (
    JinjaThemeRenderer,
    TemplateNotFoundError,
    TemplateRenderError,
)
from theme_producer.adapters.projections.registry import OPEN_PROJECTIONS
from theme_producer.adapters.template_catalog_loader import (
    MissingTemplateError,
    TemplateCatalogError,
    TemplateCatalogLoader,
    UnknownTemplateError,
)


def write_templates(directory: Path, templates: dict[str, str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in templates.items():
        (directory / name).write_text(content, encoding="utf-8")
    return directory


def test_loads_expected_catalog(tmp_path: Path) -> None:
    directory = write_templates(
        tmp_path / "templates",
        {"a.j2": "A", "b.j2": "B"},
    )

    catalog = TemplateCatalogLoader().load(["a.j2", "b.j2"], explicit_dir=directory)

    assert catalog.directory == directory.resolve()
    assert catalog.templates == ("a.j2", "b.j2")
    assert catalog.path_for("a.j2") == directory.resolve() / "a.j2"


def test_missing_template_raises(tmp_path: Path) -> None:
    directory = write_templates(tmp_path / "templates", {"a.j2": "A"})

    with pytest.raises(MissingTemplateError, match="b.j2") as excinfo:
        TemplateCatalogLoader().load(["a.j2", "b.j2"], explicit_dir=directory)

    assert excinfo.value.templates == ("b.j2",)


def test_unknown_template_raises(tmp_path: Path) -> None:
    directory = write_templates(
        tmp_path / "templates",
        {"a.j2": "A", "stray.j2": "partial"},
    )

    with pytest.raises(UnknownTemplateError, match="stray.j2") as excinfo:
        TemplateCatalogLoader().load(["a.j2"], explicit_dir=directory)

    assert excinfo.value.templates == ("stray.j2",)


def test_missing_directory_raises(tmp_path: Path) -> None:
    class _MissingResolver:
        def resolve(self, explicit_dir: Path | None = None) -> Path:
            return tmp_path / "nope"

    with pytest.raises(TemplateCatalogError, match="does not exist"):
        TemplateCatalogLoader(resolver=_MissingResolver()).load(["a.j2"])


def test_catalog_path_for_unknown_entry_raises(tmp_path: Path) -> None:
    directory = write_templates(tmp_path / "templates", {"a.j2": "A"})
    catalog = TemplateCatalogLoader().load(["a.j2"], explicit_dir=directory)

    with pytest.raises(KeyError, match="b.j2"):
        catalog.path_for("b.j2")


def test_shipped_catalog_is_one_to_one(tmp_path: Path) -> None:
    catalog = TemplateCatalogLoader().load([projection.template for projection in OPEN_PROJECTIONS])

    assert set(catalog.templates) == {projection.template for projection in OPEN_PROJECTIONS}
    assert len(catalog.templates) == len(OPEN_PROJECTIONS)


def test_renderer_rejects_unknown_template(tmp_path: Path) -> None:
    directory = write_templates(tmp_path / "templates", {"a.j2": "A"})
    renderer = JinjaThemeRenderer(templates_dir=directory)

    with pytest.raises(TemplateNotFoundError, match="missing.j2"):
        renderer.render("missing.j2", {}, tmp_path / "out")


def test_renderer_uses_strict_undefined(tmp_path: Path) -> None:
    directory = write_templates(
        tmp_path / "templates",
        {"strict.j2": "value={{ missing_value }}"},
    )
    renderer = JinjaThemeRenderer(templates_dir=directory)

    with pytest.raises(TemplateRenderError, match="missing_value"):
        renderer.render("strict.j2", {}, tmp_path / "out")


@pytest.mark.parametrize("template_name", ["", "colors.txt", "../colors.gtk.css.j2", "/tmp/x.j2"])
def test_renderer_rejects_non_catalog_names(tmp_path: Path, template_name: str) -> None:
    directory = write_templates(tmp_path / "templates", {"colors.gtk.css.j2": "x"})
    renderer = JinjaThemeRenderer(templates_dir=directory)

    with pytest.raises(ValueError):
        renderer.render(template_name, {}, tmp_path / "out")


def test_renderer_writes_template_stem_as_artifact_name(tmp_path: Path) -> None:
    directory = write_templates(
        tmp_path / "templates",
        {
            "colors.gtk.css.j2": "{{ value }}",
        },
    )
    renderer = JinjaThemeRenderer(templates_dir=directory)

    output = renderer.render("colors.gtk.css.j2", {"value": "ok"}, tmp_path / "out")

    assert output.name == "colors.gtk.css"
    assert output.read_text(encoding="utf-8") == "ok"
