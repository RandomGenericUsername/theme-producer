from __future__ import annotations

import json
from pathlib import Path

import pytest

from theme_producer.adapters.projections.registry import ALL_PROJECTIONS, ProjectionRegistry
from theme_producer.adapters.theme_json import ThemeJsonWriter
from theme_producer.domain.models import Theme

TESTS_ROOT = Path(__file__).resolve().parents[3]
THEME_FIXTURE = TESTS_ROOT / "fixtures" / "theme.json"
GOLDEN_DIR = TESTS_ROOT / "fixtures" / "projections"


def load_theme() -> Theme:
    return Theme.from_dict(json.loads(THEME_FIXTURE.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "projection",
    ALL_PROJECTIONS,
    ids=[projection.name for projection in ALL_PROJECTIONS],
)
def test_projection_matches_golden(tmp_path: Path, projection) -> None:
    output = ProjectionRegistry().render(projection, load_theme(), tmp_path)
    golden = GOLDEN_DIR / projection.filename

    assert golden.is_file(), f"missing golden snapshot: {golden}"
    assert output.read_bytes() == golden.read_bytes()


def test_golden_directory_covers_every_projection() -> None:
    expected = {projection.filename for projection in ALL_PROJECTIONS}
    actual = {path.name for path in GOLDEN_DIR.iterdir() if path.is_file()}

    assert actual == expected


def test_theme_json_matches_fixture_golden(tmp_path: Path) -> None:
    output = ThemeJsonWriter().write(load_theme(), tmp_path)

    assert output.read_text(encoding="utf-8") == THEME_FIXTURE.read_text(encoding="utf-8")
