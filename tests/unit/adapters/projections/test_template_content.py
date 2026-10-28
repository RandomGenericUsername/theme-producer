from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from theme_producer.adapters.projections.registry import ProjectionRegistry
from theme_producer.domain.enums import TONE_ORDER, MaterialRole
from theme_producer.domain.models import Theme
from theme_producer.domain.services import LEGACY_COLOR_ORDER

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "theme.json"

STABLE_NAMES = (
    "background",
    "foreground",
    "accent",
    "accent-muted",
    "surface",
    "on_surface",
    "error",
    "warning",
)

CSS_DEFINE = re.compile(r"^@define-color ([A-Za-z0-9_-]+) (#[0-9a-f]{6});$")
CONF_DEFINE = re.compile(r"^\$([A-Za-z0-9_-]+) = rgb\(([0-9a-f]{6})\)$")
YAML_SCALAR = re.compile(r'^([A-Za-z0-9_-]+): "(#[0-9a-f]{6})"$')
YAML_LIST_ITEM = re.compile(r'^  - "(#[0-9a-f]{6})"$')


@pytest.fixture(scope="module")
def theme() -> Theme:
    return Theme.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory, theme: Theme) -> dict[str, str]:
    output = tmp_path_factory.mktemp("open-projections")
    paths = ProjectionRegistry().render_all(theme, output)
    return {name: path.read_text(encoding="utf-8") for name, path in paths.items()}


def css_defines(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = CSS_DEFINE.fullmatch(line)
        if match:
            result[match.group(1)] = match.group(2)
    return result


def conf_defines(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = CONF_DEFINE.fullmatch(line)
        if match:
            result[match.group(1)] = f"#{match.group(2)}"
    return result


def role_hex(theme: Theme, role: MaterialRole) -> str:
    return theme.dark.roles[role].hex


def test_gtk_has_vocabulary_every_role_and_legacy_aliases(rendered, theme: Theme) -> None:
    defines = css_defines(rendered["colors.gtk.css"])

    for name in STABLE_NAMES:
        assert name in defines
    for role in MaterialRole:
        assert role.value in defines
    for index in range(16):
        assert f"color_{index:02d}" in defines
        assert defines[f"color_{index:02d}"] == role_hex(theme, LEGACY_COLOR_ORDER[index])
    assert len(defines) == len(set(defines))
    assert len(defines) == 8 + 46 + 16

    assert defines["background"] == role_hex(theme, MaterialRole.SURFACE)
    assert defines["foreground"] == role_hex(theme, MaterialRole.ON_SURFACE)
    assert defines["accent"] == role_hex(theme, MaterialRole.PRIMARY)


def test_adw_has_both_channels_and_no_color_scheme_property(rendered, theme: Theme) -> None:
    text = rendered["colors.adw.css"]
    defines = css_defines(text)

    assert "color-scheme:" not in text
    assert ":root {" in text
    assert "--window-bg-color:" in text
    assert "--headerbar-bg-color:" in text

    assert defines["window_bg_color"] == role_hex(theme, MaterialRole.SURFACE)
    assert defines["view_bg_color"] == role_hex(theme, MaterialRole.SURFACE)
    assert defines["dialog_bg_color"] == role_hex(theme, MaterialRole.SURFACE)
    assert defines["headerbar_bg_color"] == role_hex(theme, MaterialRole.SURFACE_CONTAINER)
    assert defines["card_bg_color"] == role_hex(theme, MaterialRole.SURFACE_CONTAINER_LOW)
    assert defines["popover_bg_color"] == role_hex(theme, MaterialRole.SURFACE_CONTAINER_HIGH)
    assert defines["sidebar_bg_color"] == role_hex(theme, MaterialRole.SURFACE_CONTAINER_HIGH)
    assert defines["window_fg_color"] == role_hex(theme, MaterialRole.ON_SURFACE)
    assert defines["accent_color"] == role_hex(theme, MaterialRole.PRIMARY)
    assert defines["accent_bg_color"] == role_hex(theme, MaterialRole.PRIMARY)
    assert defines["accent_fg_color"] == role_hex(theme, MaterialRole.ON_PRIMARY)
    assert defines["destructive_color"] == role_hex(theme, MaterialRole.ERROR)
    assert defines["destructive_fg_color"] == role_hex(theme, MaterialRole.ON_ERROR)
    assert defines["success_color"] == role_hex(theme, MaterialRole.TERTIARY)
    assert defines["success_fg_color"] == role_hex(theme, MaterialRole.ON_TERTIARY)
    assert defines["warning_color"] == role_hex(theme, MaterialRole.SECONDARY)
    assert defines["warning_fg_color"] == role_hex(theme, MaterialRole.ON_SECONDARY)
    assert defines["error_color"] == role_hex(theme, MaterialRole.ERROR)
    assert defines["error_fg_color"] == role_hex(theme, MaterialRole.ON_ERROR)

    assert "--accent-bg-color: " + role_hex(theme, MaterialRole.PRIMARY) + ";" in text
    assert "--success-bg-color: " + role_hex(theme, MaterialRole.TERTIARY) + ";" in text
    assert "--warning-bg-color: " + role_hex(theme, MaterialRole.SECONDARY) + ";" in text

    for name in STABLE_NAMES:
        assert name in defines
    for role in MaterialRole:
        assert role.value in defines
    for index in range(16):
        assert f"color_{index:02d}" in defines
    assert len(defines) == len(set(defines))


def test_yaml_has_vocabulary_cursor_all_roles_and_legacy_list(rendered, theme: Theme) -> None:
    text = rendered["colors.yaml"]
    scalars: list[tuple[str, str]] = []
    colors: list[str] = []
    in_colors = False
    for line in text.splitlines():
        if line == "colors:":
            in_colors = True
            continue
        if not line or line.startswith("#"):
            continue
        if in_colors:
            match = YAML_LIST_ITEM.fullmatch(line)
            assert match is not None, f"unexpected YAML list line: {line!r}"
            colors.append(match.group(1))
            continue
        match = YAML_SCALAR.fullmatch(line)
        assert match is not None, f"unexpected YAML line: {line!r}"
        scalars.append((match.group(1), match.group(2)))

    keys = [key for key, _value in scalars]
    values = dict(scalars)

    for name in ("background", "foreground", "cursor", *STABLE_NAMES):
        assert name in values
    for role in MaterialRole:
        assert role.value in values
    assert len(keys) == len(set(keys)), "colors.yaml must not emit duplicate keys"

    assert values["background"] == role_hex(theme, MaterialRole.SURFACE)
    assert values["foreground"] == role_hex(theme, MaterialRole.ON_SURFACE)
    assert values["cursor"] == role_hex(theme, MaterialRole.ON_SURFACE)
    assert values["accent"] == role_hex(theme, MaterialRole.PRIMARY)
    assert colors == [role_hex(theme, role) for role in LEGACY_COLOR_ORDER]


def test_rasi_has_vocabulary_roles_and_legacy_aliases(rendered, theme: Theme) -> None:
    defines = css_defines(rendered["colors.rasi"])

    for name in STABLE_NAMES:
        assert name in defines
    for role in MaterialRole:
        assert role.value in defines
    for index in range(16):
        assert f"color{index}" in defines
        assert defines[f"color{index}"] == role_hex(theme, LEGACY_COLOR_ORDER[index])
    assert len(defines) == len(set(defines))
    assert defines["background"] == role_hex(theme, MaterialRole.SURFACE)
    assert defines["foreground"] == role_hex(theme, MaterialRole.ON_SURFACE)
    assert defines["accent"] == role_hex(theme, MaterialRole.PRIMARY)


def test_conf_uses_hyprland_rgb_variables_without_hashes(rendered, theme: Theme) -> None:
    text = rendered["colors.conf"]
    assert "#" not in text
    assert ";" not in text
    assert '"' not in text

    defines = conf_defines(text)
    for name in STABLE_NAMES:
        assert name in defines
    for role in MaterialRole:
        assert role.value in defines
    for index in range(16):
        assert f"color{index}" in defines
        assert defines[f"color{index}"] == role_hex(theme, LEGACY_COLOR_ORDER[index])
    assert len(defines) == len(set(defines))
    assert defines["background"] == role_hex(theme, MaterialRole.SURFACE)
    assert defines["foreground"] == role_hex(theme, MaterialRole.ON_SURFACE)
    assert defines["accent"] == role_hex(theme, MaterialRole.PRIMARY)


def test_btop_renders_the_capability_table(rendered) -> None:
    lines = [
        line
        for line in rendered["colors.btop.theme"].splitlines()
        if line and not line.startswith("#")
    ]

    assert len(lines) == 48
    assert all(line.startswith("theme[") for line in lines)


def test_html_shows_mode_scheme_roles_and_all_palettes(rendered, theme: Theme) -> None:
    text = rendered["theme.html"]

    assert "<!DOCTYPE html>" in text
    assert "mode: <strong>dark</strong>" in text
    assert theme.scheme in text
    assert text.count('class="role"') == 50
    assert text.count('class="tone"') == 6 * 18
    for role in MaterialRole:
        assert role.value in text
    for palette in ("primary", "secondary", "tertiary", "neutral", "neutral_variant", "error"):
        assert palette in text
    for palette in theme.dark.palettes.values():
        for tone in TONE_ORDER:
            assert f">{tone}<br>{palette.tones[tone].hex}" in text
