from __future__ import annotations

import json
from pathlib import Path

import pytest

from theme_producer.adapters.jinja_renderer import JinjaThemeRenderer
from theme_producer.adapters.projections.registry import (
    CAPABILITY_TABLE,
    DEV_PROJECTIONS,
    OPEN_PROJECTIONS,
    PROJECTION_VOCABULARY,
    RUNTIME_PROJECTIONS,
    ProjectionRegistry,
    build_projection_context,
)
from theme_producer.domain.enums import TONE_ORDER, MaterialRole, PaletteName
from theme_producer.domain.models import Theme
from theme_producer.domain.services import LEGACY_COLOR_ORDER
from theme_producer.ports.projection import Projection, ProjectionPort

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "theme.json"

EXPECTED_PROJECTIONS = (
    ("gtk", "colors.gtk.css", "open", False),
    ("adw", "colors.adw.css", "open", False),
    ("yaml", "colors.yaml", "open", False),
    ("rasi", "colors.rasi", "open", False),
    ("conf", "colors.conf", "open", False),
    ("btop", "colors.btop.theme", "open", False),
    ("html", "theme.html", "open", True),
)


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_open_projection_table_is_pinned() -> None:
    assert (
        tuple((p.name, p.filename, p.capability, p.dev_only) for p in OPEN_PROJECTIONS)
        == EXPECTED_PROJECTIONS
    )


def test_capability_table_is_all_open_for_req_008() -> None:
    assert set(CAPABILITY_TABLE) == {name for name, *_rest in EXPECTED_PROJECTIONS}
    assert set(CAPABILITY_TABLE.values()) == {"open"}


def test_dev_and_runtime_sets_are_disjoint_and_complete() -> None:
    assert DEV_PROJECTIONS == tuple(p for p in OPEN_PROJECTIONS if p.dev_only)
    assert RUNTIME_PROJECTIONS == tuple(p for p in OPEN_PROJECTIONS if not p.dev_only)
    assert set(DEV_PROJECTIONS) | set(RUNTIME_PROJECTIONS) == set(OPEN_PROJECTIONS)
    assert [p.filename for p in DEV_PROJECTIONS] == ["theme.html"]


def test_registry_renders_every_projection(tmp_path: Path) -> None:
    theme = load_theme()
    registry = ProjectionRegistry()

    rendered = registry.render_all(theme, tmp_path)

    assert set(rendered) == {projection.filename for projection in OPEN_PROJECTIONS}
    for filename, path in rendered.items():
        assert path == tmp_path / filename
        assert path.is_file()
        assert path.read_text(encoding="utf-8")


def test_render_runtime_excludes_dev_preview(tmp_path: Path) -> None:
    rendered = ProjectionRegistry().render_runtime(load_theme(), tmp_path)

    assert set(rendered) == {projection.filename for projection in RUNTIME_PROJECTIONS}
    assert "theme.html" not in rendered


def test_render_one_by_name(tmp_path: Path) -> None:
    output = ProjectionRegistry().render("btop", load_theme(), tmp_path)

    assert output == tmp_path / "colors.btop.theme"
    assert output.is_file()


def test_render_one_by_metadata(tmp_path: Path) -> None:
    projection = next(p for p in OPEN_PROJECTIONS if p.name == "gtk")

    output = ProjectionRegistry().render(projection, load_theme(), tmp_path)

    assert output == tmp_path / "colors.gtk.css"


def test_unknown_projection_name_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="unknown projection 'nope'"):
        ProjectionRegistry().render("nope", load_theme(), tmp_path)


def test_unregistered_projection_metadata_raises(tmp_path: Path) -> None:
    stray = Projection(
        name="stray",
        filename="colors.stray",
        capability="open",
        template="colors.stray.j2",
    )

    with pytest.raises(KeyError, match="not registered"):
        ProjectionRegistry().render(stray, load_theme(), tmp_path)


def test_registry_exposes_projection_port_implementations(tmp_path: Path) -> None:
    registry = ProjectionRegistry()

    for projection in OPEN_PROJECTIONS:
        renderer = registry.renderer_for(projection.name)
        assert isinstance(renderer, ProjectionPort)
        output = renderer.render(load_theme(), tmp_path / projection.name)
        assert output == tmp_path / projection.name / projection.filename


def test_registry_is_deterministic(tmp_path: Path) -> None:
    theme = load_theme()
    registry = ProjectionRegistry()

    first = registry.render_all(theme, tmp_path / "one")
    second = registry.render_all(theme, tmp_path / "two")

    assert set(first) == set(second)
    for filename in first:
        assert first[filename].read_bytes() == second[filename].read_bytes()


def test_context_exposes_the_stable_vocabulary() -> None:
    theme = load_theme()
    context = build_projection_context(theme)
    vocabulary = dict(context.vocabulary)

    assert tuple(vocabulary) == tuple(PROJECTION_VOCABULARY)
    assert vocabulary["background"] == theme.dark.roles[MaterialRole.SURFACE]
    assert vocabulary["foreground"] == theme.dark.roles[MaterialRole.ON_SURFACE]
    assert vocabulary["accent"] == theme.dark.roles[MaterialRole.PRIMARY]
    assert vocabulary["accent-muted"] == theme.dark.roles[MaterialRole.SECONDARY]
    assert vocabulary["warning"] == theme.dark.roles[MaterialRole.TERTIARY]
    assert context.mode_name == "dark"


def test_context_exposes_all_roles_legacy_aliases_and_palettes() -> None:
    theme = load_theme()
    context = build_projection_context(theme)
    legacy = dict(context.legacy)

    assert len(context.roles) == 50
    assert {name for name, _color in context.roles} == {role.value for role in MaterialRole}
    assert len(context.extra_roles) == 46
    assert list(legacy) == [f"color{index}" for index in range(16)]
    for index, role in enumerate(LEGACY_COLOR_ORDER):
        assert legacy[f"color{index}"] == theme.dark.roles[role]
    assert tuple(name for name, _tones in context.palettes) == tuple(
        name.value for name in PaletteName
    )
    assert len(context.palettes) == 6
    for _name, tones in context.palettes:
        assert tuple(tone for tone, _color in tones) == TONE_ORDER
        assert len(tones) == 18
    assert len(context.btop) == 48


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"name": "", "filename": "x", "capability": "open", "template": "x.j2"}, "name"),
        ({"name": "x", "filename": "", "capability": "open", "template": "x.j2"}, "filename"),
        (
            {"name": "x", "filename": "a/b", "capability": "open", "template": "x.j2"},
            "basename",
        ),
        (
            {"name": "x", "filename": "x", "capability": "closed", "template": "x.j2"},
            "capability",
        ),
        ({"name": "x", "filename": "x", "capability": "open", "template": "x"}, "j2"),
    ],
)
def test_projection_metadata_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        Projection(**kwargs)


def test_registry_accepts_an_explicit_template_directory(tmp_path: Path) -> None:
    theme = load_theme()
    templates = (
        Path(__file__).resolve().parents[4] / "src" / "theme_producer" / "defaults" / "templates"
    )
    renderer = JinjaThemeRenderer(templates_dir=templates)
    registry = ProjectionRegistry(templates_dir=templates, renderer=renderer)

    output = registry.render("gtk", theme, tmp_path)

    assert output.is_file()
