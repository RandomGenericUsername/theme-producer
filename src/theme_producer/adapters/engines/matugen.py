"""matugen v1 engine adapter.

matugen is used strictly as an external process: a minimal isolated config,
``--json hex --dry-run``, and a source selector on every invocation. No
templates, hooks, wallpaper, or host config are read, and no matugen code is
imported or linked (GPL containment, AD-3/AD-10).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

from theme_producer.domain.engine_params import ParameterResolutionService
from theme_producer.domain.engines import (
    EngineConfig,
    EngineParameterDefinition,
    ThemeRequest,
)
from theme_producer.domain.enums import MaterialRole, ModeName, PaletteName, SourceKind
from theme_producer.domain.exceptions import (
    EngineConfigError,
    EngineExecutionError,
    EngineNotAvailableError,
    EngineParseError,
    ThemeValidationError,
)
from theme_producer.domain.models import (
    SCHEMA_VERSION,
    Color,
    GeneratorMetadata,
    Mode,
    Source,
    Theme,
    TonalPalette,
)

__all__ = ["MATUGEN_PARAMETERS", "MatugenEngine"]

ENGINE_NAME = "matugen"
BINARY_NAME = "matugen"
FALLBACK_VERSION = "4.2.0"

_MINIMAL_CONFIG = "[config]\n\n[templates]\n"

_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

#: The catalog's matugen parameter defaults, restated here so the adapter is
#: usable without the loader (the catalog remains the user-facing source).
MATUGEN_PARAMETERS: tuple[EngineParameterDefinition, ...] = (
    EngineParameterDefinition(
        name="mode",
        param_type="str",
        default="dark",
        choices=("dark", "light", "smart"),
        description="Matugen color mode",
    ),
    EngineParameterDefinition(
        name="scheme_type",
        param_type="str",
        default="scheme-tonal-spot",
        choices=(
            "scheme-content",
            "scheme-expressive",
            "scheme-fidelity",
            "scheme-fruit-salad",
            "scheme-monochrome",
            "scheme-neutral",
            "scheme-rainbow",
            "scheme-tonal-spot",
            "scheme-vibrant",
            "scheme-smart",
        ),
        description="Material color scheme type",
    ),
    EngineParameterDefinition(
        name="contrast",
        param_type="float",
        default=0.0,
        description="Contrast adjustment in [-1, 1]",
    ),
    EngineParameterDefinition(
        name="lightness_dark",
        param_type="float",
        default=0.0,
        description="Dark-mode lightness shift in [-1, 1] (0 = unchanged)",
    ),
    EngineParameterDefinition(
        name="lightness_light",
        param_type="float",
        default=0.0,
        description="Light-mode lightness shift in [-1, 1] (0 = unchanged)",
    ),
    EngineParameterDefinition(
        name="source_color_index",
        param_type="int",
        default=0,
        description="Which extracted source color to use (0-3)",
    ),
    EngineParameterDefinition(
        name="prefer",
        param_type="str",
        default="",
        choices=(
            "",
            "darkness",
            "lightness",
            "saturation",
            "less-saturation",
            "value",
            "closest-to-fallback",
        ),
        description="Which extracted source color to prefer (empty uses source_color_index)",
    ),
    EngineParameterDefinition(
        name="timeout",
        param_type="int",
        default=300,
        description="Subprocess timeout in seconds",
    ),
    EngineParameterDefinition(
        name="fallback_color",
        param_type="str",
        default="",
        description="Optional seed color used when extraction is inconclusive",
    ),
)


class MatugenEngine:
    """Generate a Theme by running the pinned matugen binary."""

    name = ENGINE_NAME

    def is_available(self) -> bool:
        """Return whether ``matugen`` is on PATH."""
        return shutil.which(BINARY_NAME) is not None

    def generate(self, request: ThemeRequest, config: EngineConfig) -> Theme:
        """Run matugen for one source and parse the JSON response into a Theme."""
        if request.source_kind is SourceKind.JSON:
            raise EngineConfigError(
                "source_kind",
                "json source is handled by the CLI",
            )

        params = ParameterResolutionService.resolve_all(MATUGEN_PARAMETERS, config.params)
        mode = str(params["mode"])
        scheme = str(params["scheme_type"])
        contrast = _clamp_float(params["contrast"], -1.0, 1.0, "contrast")
        lightness_dark = _clamp_float(
            params["lightness_dark"], -1.0, 1.0, "lightness_dark"
        )
        lightness_light = _clamp_float(
            params["lightness_light"], -1.0, 1.0, "lightness_light"
        )
        source_color_index = _clamp_int(params["source_color_index"], 0, 3)
        prefer = _normalize_prefer(params["prefer"])
        fallback_color = _normalize_fallback(params["fallback_color"])
        timeout = _effective_timeout(config)

        source, argv_source = _build_source(request)
        argv = _build_argv(
            argv_source=argv_source,
            mode=mode,
            scheme=scheme,
            contrast=contrast,
            lightness_dark=lightness_dark,
            lightness_light=lightness_light,
            source_color_index=source_color_index,
            prefer=prefer,
            fallback_color=fallback_color,
        )

        config_path: str | None = None
        try:
            config_path = _write_minimal_config()
            argv = [*argv, "--config", config_path, "--quiet"]

            result = _run(argv, timeout=timeout)
            if result.returncode != 0:
                raise EngineExecutionError(
                    ENGINE_NAME,
                    f"exited with status {result.returncode}",
                    stderr=_text(result.stderr),
                    returncode=result.returncode,
                )
            payload = _decode_payload(result.stdout)
            return _build_theme(
                payload,
                source=source,
                scheme=scheme,
                contrast=contrast,
            )
        finally:
            if config_path is not None:
                Path(config_path).unlink(missing_ok=True)


@lru_cache(maxsize=1)
def _engine_version() -> str:
    """Return matugen's version, falling back to the pinned version."""
    if shutil.which(BINARY_NAME) is None:
        return FALLBACK_VERSION
    try:
        result = subprocess.run(
            [BINARY_NAME, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
    except OSError, subprocess.SubprocessError:
        return FALLBACK_VERSION

    if result.returncode != 0:
        return FALLBACK_VERSION
    for stream in (result.stdout, result.stderr):
        tokens = (stream or "").strip().split()
        if tokens and _VERSION_PATTERN.fullmatch(tokens[-1]):
            return tokens[-1]
    return FALLBACK_VERSION


def _effective_timeout(config: EngineConfig) -> int:
    raw = config.params.get("timeout", config.timeout)
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        raise EngineConfigError("timeout", f"must be a number; got {raw!r}")
    try:
        timeout = int(raw)
    except (TypeError, ValueError) as exc:
        raise EngineConfigError("timeout", f"must be a number; got {raw!r}") from exc
    return max(1, timeout)


def _clamp_float(value: Any, low: float, high: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EngineConfigError(name, f"must be a number; got {value!r}") from exc
    if number != number:  # NaN
        raise EngineConfigError(name, f"must be a number; got {value!r}")
    return max(low, min(high, number))


def _clamp_int(value: Any, low: int, high: int) -> int:
    if isinstance(value, bool):
        raise EngineConfigError("source_color_index", f"must be an int; got {value!r}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise EngineConfigError("source_color_index", f"must be an int; got {value!r}") from exc
    return max(low, min(high, number))


def _normalize_prefer(value: Any) -> str:
    """Return the preference name, or ``""`` when the index selects the color."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise EngineConfigError("prefer", f"must be a string; got {value!r}")
    return value.strip()


def _normalize_fallback(value: Any) -> str:
    """Return a validated ``#rrggbb`` fallback, or ``""`` when unset."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise EngineConfigError("fallback_color", f"must be a string; got {value!r}")
    fallback = value.strip()
    if not fallback:
        return ""
    if not _COLOR_PATTERN.fullmatch(fallback):
        raise EngineConfigError(
            "fallback_color",
            f"expected #rrggbb or #rrggbbaa; got {fallback!r}",
        )
    return fallback[:7].lower()


def _build_source(request: ThemeRequest) -> tuple[Source, str]:
    if request.source_kind is SourceKind.IMAGE:
        assert request.image_path is not None
        image_path = request.image_path.expanduser().resolve()
        if not image_path.is_file():
            raise EngineConfigError("image_path", f"not a file: {image_path}")
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise EngineConfigError("image_path", f"cannot read {image_path}: {exc}") from exc
        return (
            Source(
                kind=SourceKind.IMAGE,
                path=str(image_path),
                hash=sha256(image_bytes).hexdigest(),
            ),
            str(image_path),
        )

    if request.source_kind is SourceKind.COLOR:
        assert request.color is not None
        color = request.color.strip()
        if not _COLOR_PATTERN.fullmatch(color):
            raise EngineConfigError(
                "color",
                f"expected #rrggbb or #rrggbbaa; got {color!r}",
            )
        # matugen's color subcommand takes a 6-digit hex string.
        argv_color = color[:7].lower()
        return (
            Source(
                kind=SourceKind.COLOR,
                path=None,
                hash=sha256(color.encode("utf-8")).hexdigest(),
            ),
            argv_color,
        )

    raise EngineConfigError("source_kind", "json source is handled by the CLI")


def _build_argv(
    *,
    argv_source: str,
    mode: str,
    scheme: str,
    contrast: float,
    lightness_dark: float = 0.0,
    lightness_light: float = 0.0,
    source_color_index: int,
    prefer: str = "",
    fallback_color: str = "",
) -> list[str]:
    lightness = [
        "--lightness-dark",
        str(lightness_dark),
        "--lightness-light",
        str(lightness_light),
    ]
    if not _is_color_source(argv_source):
        argv = [
            BINARY_NAME,
            "image",
            argv_source,
            "--json",
            "hex",
            "--dry-run",
            "--mode",
            mode,
            "--type",
            scheme,
            "--contrast",
            str(contrast),
            *lightness,
        ]
        # matugen gives --source-color-index precedence over --prefer, so the
        # index is only forwarded when no preference is configured.
        if prefer:
            argv.extend(["--prefer", prefer])
        else:
            argv.extend(["--source-color-index", str(source_color_index)])
        if fallback_color:
            argv.extend(["--fallback-color", fallback_color])
        argv.extend(["--base16-backend", "wal"])
        return argv
    return [
        BINARY_NAME,
        "color",
        "hex",
        argv_source,
        "--json",
        "hex",
        "--dry-run",
        "--mode",
        mode,
        "--type",
        scheme,
        "--contrast",
        str(contrast),
        *lightness,
    ]


def _is_color_source(value: str) -> bool:
    return value.startswith("#")


def _write_minimal_config() -> str:
    descriptor, path = tempfile.mkstemp(prefix="tpr-matugen-", suffix=".toml")
    try:
        with open(descriptor, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(_MINIMAL_CONFIG)
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
    return path


def _run(argv: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise EngineNotAvailableError(
            ENGINE_NAME,
            "install matugen 4.2.0 or use the pinned engine image",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise EngineExecutionError(
            ENGINE_NAME,
            f"timed out after {timeout}s",
            stderr=_text(exc.stderr),
        ) from exc
    except OSError as exc:
        raise EngineExecutionError(ENGINE_NAME, f"could not start process: {exc}") from exc

    # Unreachable: subprocess.run returns or raises above. Kept for clarity.
    raise AssertionError("unreachable")


def _decode_payload(stdout: str | bytes | None) -> Mapping[str, Any]:
    text = _text(stdout)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EngineParseError(ENGINE_NAME, f"invalid JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise EngineParseError(
            ENGINE_NAME,
            f"expected a JSON object; got {type(payload).__name__}",
        )
    return payload


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _build_theme(
    payload: Mapping[str, Any],
    *,
    source: Source,
    scheme: str,
    contrast: float,
) -> Theme:
    try:
        dark_roles, light_roles = _parse_roles(payload)
        dark_palettes, light_palettes = _parse_palettes(payload)
        return Theme(
            source=source,
            scheme=scheme,
            contrast=contrast,
            dark=Mode(mode=ModeName.DARK, roles=dark_roles, palettes=dark_palettes),
            light=Mode(mode=ModeName.LIGHT, roles=light_roles, palettes=light_palettes),
            generator=GeneratorMetadata(
                engine=ENGINE_NAME,
                engine_version=_engine_version(),
                schema_version=SCHEMA_VERSION,
            ),
        )
    except ThemeValidationError as exc:
        raise EngineParseError(ENGINE_NAME, str(exc)) from exc


def _parse_roles(
    payload: Mapping[str, Any],
) -> tuple[dict[MaterialRole, Color], dict[MaterialRole, Color]]:
    raw_colors = payload.get("colors")
    if not isinstance(raw_colors, Mapping):
        raise EngineParseError(ENGINE_NAME, "missing or invalid 'colors' object")

    dark: dict[MaterialRole, Color] = {}
    light: dict[MaterialRole, Color] = {}
    for role in MaterialRole:
        role_payload = raw_colors.get(role.value)
        if not isinstance(role_payload, Mapping):
            raise EngineParseError(ENGINE_NAME, f"missing role {role.value!r} in 'colors'")
        dark[role] = _parse_color(
            role_payload.get(ModeName.DARK.value), f"colors.{role.value}.dark"
        )
        light[role] = _parse_color(
            role_payload.get(ModeName.LIGHT.value), f"colors.{role.value}.light"
        )
    return dark, light


def _parse_palettes(
    payload: Mapping[str, Any],
) -> tuple[dict[PaletteName, TonalPalette], dict[PaletteName, TonalPalette]]:
    raw_palettes = payload.get("palettes")
    if not isinstance(raw_palettes, Mapping):
        raise EngineParseError(ENGINE_NAME, "missing or invalid 'palettes' object")

    # matugen palette tones are mode-independent: the same 18 tones serve both
    # dark and light modes.
    dark: dict[PaletteName, TonalPalette] = {}
    light: dict[PaletteName, TonalPalette] = {}
    for palette_name in PaletteName:
        tones_payload = raw_palettes.get(palette_name.value)
        if not isinstance(tones_payload, Mapping):
            raise EngineParseError(
                ENGINE_NAME,
                f"missing palette {palette_name.value!r} in 'palettes'",
            )
        tones: dict[int, Color] = {}
        for raw_tone, node in tones_payload.items():
            try:
                tone = int(raw_tone)
            except (TypeError, ValueError) as exc:
                raise EngineParseError(
                    ENGINE_NAME,
                    f"palette {palette_name.value!r} has non-integer tone {raw_tone!r}",
                ) from exc
            tones[tone] = _parse_color(node, f"palettes.{palette_name.value}.{raw_tone}")
        dark[palette_name] = TonalPalette(name=palette_name, tones=tones)
        light[palette_name] = TonalPalette(name=palette_name, tones=dict(tones))
    return dark, light


def _parse_color(node: Any, context: str) -> Color:
    if not isinstance(node, Mapping):
        raise EngineParseError(ENGINE_NAME, f"{context} must be an object with 'color'")
    raw = node.get("color")
    if not isinstance(raw, str):
        raise EngineParseError(ENGINE_NAME, f"{context}.color must be a hex string")
    value = raw.strip()
    if len(value) == 9:
        value = value[:7]
    if not _COLOR_PATTERN.fullmatch(raw.strip()) or len(value) != 7:
        raise EngineParseError(ENGINE_NAME, f"{context}.color is not a hex color: {raw!r}")
    return Color.from_hex(value.lower())
