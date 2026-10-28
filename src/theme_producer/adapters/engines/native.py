"""Native v2 engine adapter.

The Rust helper ``tpr-native`` (see ``native/``) generates the canonical
``theme.json`` shape with the MIT/Apache-2.0 ``material-colors`` crate. This
adapter owns request validation and process containment; it never imports or
links Rust code, exactly like the matugen adapter.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from theme_producer.domain.engine_params import ParameterResolutionService
from theme_producer.domain.engines import (
    EngineConfig,
    EngineParameterDefinition,
    ThemeRequest,
)
from theme_producer.domain.enums import SourceKind
from theme_producer.domain.exceptions import (
    EngineConfigError,
    EngineExecutionError,
    EngineNotAvailableError,
    EngineParseError,
    ThemeValidationError,
)
from theme_producer.domain.models import Theme

__all__ = ["NATIVE_PARAMETERS", "NativeEngine"]

ENGINE_NAME = "native"
BINARY_NAME = "tpr-native"

_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$")

#: The catalog's native parameter defaults, restated here so the adapter is
#: usable without the loader. They intentionally match matugen's surface: both
#: engines accept the same ThemeRequest and produce the same canonical Theme.
NATIVE_PARAMETERS: tuple[EngineParameterDefinition, ...] = (
    EngineParameterDefinition(
        name="mode",
        param_type="str",
        default="dark",
        choices=("dark", "light", "smart"),
        description="Color mode",
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
        name="source_color_index",
        param_type="int",
        default=0,
        description="Which extracted source color to use (0-4)",
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


class NativeEngine:
    """Generate a Theme by running the pinned ``tpr-native`` binary."""

    name = ENGINE_NAME

    def is_available(self) -> bool:
        """Return whether ``tpr-native`` is on PATH."""
        return shutil.which(BINARY_NAME) is not None

    def generate(self, request: ThemeRequest, config: EngineConfig) -> Theme:
        """Run the native helper for one source and parse its canonical JSON."""
        if request.source_kind is SourceKind.JSON:
            raise EngineConfigError(
                "source_kind",
                "json source is handled by the CLI",
            )

        params = ParameterResolutionService.resolve_all(NATIVE_PARAMETERS, config.params)
        scheme = str(params["scheme_type"])
        contrast = _clamp_float(params["contrast"], -1.0, 1.0)
        source_color_index = _clamp_int(params["source_color_index"], 0, 4)
        prefer = _normalize_prefer(params["prefer"])
        fallback_color = _normalize_fallback(params["fallback_color"])
        timeout = _effective_timeout(config)

        argv, color_hash = _build_argv(
            request,
            scheme=scheme,
            contrast=contrast,
            source_color_index=source_color_index,
            prefer=prefer,
            fallback_color=fallback_color,
        )
        result = _run(argv, timeout=timeout)
        if result.returncode != 0:
            raise EngineExecutionError(
                ENGINE_NAME,
                f"exited with status {result.returncode}",
                stderr=_text(result.stderr),
                returncode=result.returncode,
            )

        payload = dict(_decode_payload(result.stdout))
        if color_hash is not None:
            payload["source"] = {
                "kind": SourceKind.COLOR.value,
                "path": None,
                "hash": color_hash,
            }
        return _build_theme(payload)


def _effective_timeout(config: EngineConfig) -> int:
    raw = config.params.get("timeout", config.timeout)
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        raise EngineConfigError("timeout", f"must be a number; got {raw!r}")
    try:
        timeout = int(raw)
    except (TypeError, ValueError) as exc:
        raise EngineConfigError("timeout", f"must be a number; got {raw!r}") from exc
    return max(1, timeout)


def _clamp_float(value: Any, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EngineConfigError("contrast", f"must be a number; got {value!r}") from exc
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


def _build_argv(
    request: ThemeRequest,
    *,
    scheme: str,
    contrast: float,
    source_color_index: int,
    prefer: str = "",
    fallback_color: str = "",
) -> tuple[list[str], str | None]:
    argv = [BINARY_NAME]
    color_hash: str | None = None

    if request.source_kind is SourceKind.IMAGE:
        assert request.image_path is not None
        image_path = request.image_path.expanduser().resolve()
        if not image_path.is_file():
            raise EngineConfigError("image_path", f"not a file: {image_path}")
        argv.extend(["--image", str(image_path)])
    elif request.source_kind is SourceKind.COLOR:
        assert request.color is not None
        color = request.color.strip()
        if not _COLOR_PATTERN.fullmatch(color):
            raise EngineConfigError(
                "color",
                f"expected #rrggbb or #rrggbbaa; got {color!r}",
            )
        argv.extend(["--color", color[:7].lower()])
        color_hash = sha256(color.encode("utf-8")).hexdigest()
    else:
        raise EngineConfigError("source_kind", "json source is handled by the CLI")

    argv.extend(
        [
            "--scheme",
            scheme,
            "--contrast",
            str(contrast),
        ]
    )
    if request.source_kind is SourceKind.IMAGE:
        # An explicit index wins over --prefer in the helper, so only forward it
        # when no preference is configured.
        if prefer:
            argv.extend(["--prefer", prefer])
        else:
            argv.extend(["--source-color-index", str(source_color_index)])
        if fallback_color:
            argv.extend(["--fallback-color", fallback_color])
    argv.append("--json")
    return argv, color_hash


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
            "build native/ (`cargo build --release --locked`) and put tpr-native "
            "on PATH, or use the pinned native engine image",
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


def _build_theme(payload: Mapping[str, Any]) -> Theme:
    try:
        return Theme.from_dict(payload)
    except ThemeValidationError as exc:
        raise EngineParseError(ENGINE_NAME, str(exc)) from exc
