from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import theme_producer.adapters.engines.native as native_module
from theme_producer.adapters.engines.native import NativeEngine
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.enums import MaterialRole, ModeName, PaletteName, SourceKind
from theme_producer.domain.exceptions import (
    EngineConfigError,
    EngineExecutionError,
    EngineNotAvailableError,
    EngineParseError,
)

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "theme.json"


def _payload(
    image: Path | None = None,
    *,
    scheme: str = "scheme-tonal-spot",
    contrast: float = 0.0,
) -> dict[str, Any]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["generator"] = {
        "engine": "native",
        "engine_version": "0.1.0",
        "schema_version": "1",
    }
    payload["scheme"] = scheme
    payload["contrast"] = contrast
    if image is not None:
        payload["source"] = {
            "kind": "image",
            "path": str(image.resolve()),
            "hash": sha256(image.read_bytes()).hexdigest(),
        }
    return payload


def _install_fake_run(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any] | str,
    *,
    returncode: int = 0,
    stderr: str = "",
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"argv": list(argv), "kwargs": kwargs})
        stdout = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(native_module.subprocess, "run", fake_run)
    return calls


def _install_raising_run(
    monkeypatch: pytest.MonkeyPatch,
    exc: BaseException,
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        raise exc

    monkeypatch.setattr(native_module.subprocess, "run", fake_run)
    return calls


def _image_request(tmp_path: Path) -> tuple[ThemeRequest, Path]:
    image = tmp_path / "wall.png"
    image.write_bytes(b"not-really-a-png-but-stable-bytes")
    return ThemeRequest(source_kind="image", image_path=image), image


def _argv_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def test_generate_parses_both_modes_and_palettes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, image = _image_request(tmp_path)
    calls = _install_fake_run(
        monkeypatch, _payload(image, scheme="scheme-vibrant", contrast=0.5)
    )
    config = EngineConfig(
        engine="native",
        params={
            "mode": "light",
            "scheme_type": "scheme-vibrant",
            "contrast": 0.5,
            "source_color_index": 2,
        },
        timeout=42,
    )

    theme = NativeEngine().generate(request, config)

    for mode in (theme.dark, theme.light):
        assert len(mode.roles) == 50
        assert set(mode.roles) == set(MaterialRole)
        assert len(mode.palettes) == 6
        assert set(mode.palettes) == set(PaletteName)
        assert all(len(palette.tones) == 18 for palette in mode.palettes.values())

    assert theme.source.kind is SourceKind.IMAGE
    assert theme.source.path == str(image.resolve())
    assert theme.source.hash == sha256(image.read_bytes()).hexdigest()
    assert theme.scheme == "scheme-vibrant"
    assert theme.contrast == 0.5
    assert theme.dark.mode is ModeName.DARK
    assert theme.light.mode is ModeName.LIGHT
    assert theme.generator.engine == "native"
    assert theme.generator.engine_version == "0.1.0"
    assert theme.generator.schema_version == "1"

    assert len(calls) == 1
    argv = calls[0]["argv"]
    assert argv[0] == "tpr-native"
    assert argv[1:3] == ["--image", str(image.resolve())]
    assert _argv_value(argv, "--scheme") == "scheme-vibrant"
    assert _argv_value(argv, "--contrast") == "0.5"
    assert _argv_value(argv, "--source-color-index") == "2"
    assert argv[-1] == "--json"
    assert calls[0]["kwargs"]["shell"] is False
    assert calls[0]["kwargs"]["timeout"] == 42
    assert calls[0]["kwargs"]["capture_output"] is True
    assert calls[0]["kwargs"]["text"] is True


def test_color_source_argv_and_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="color", color="#FF0000")
    config = EngineConfig(engine="native", params={}, timeout=10)

    theme = NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert argv[1:3] == ["--color", "#ff0000"]
    assert "--source-color-index" not in argv
    assert "--image" not in argv
    assert _argv_value(argv, "--scheme") == "scheme-tonal-spot"
    assert argv[-1] == "--json"

    assert theme.source.kind is SourceKind.COLOR
    assert theme.source.path is None
    assert theme.source.hash == sha256(b"#FF0000").hexdigest()


def test_eight_digit_hex_alpha_is_stripped_for_the_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="color", color="#11223380")

    theme = NativeEngine().generate(request, EngineConfig(engine="native"))

    assert calls[0]["argv"][1:3] == ["--color", "#112233"]
    assert theme.source.hash == sha256(b"#11223380").hexdigest()


def test_json_source_is_rejected_before_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="json", json_path=tmp_path / "theme.json")

    with pytest.raises(EngineConfigError, match="json source"):
        NativeEngine().generate(request, EngineConfig(engine="native"))

    assert calls == []


def test_contrast_index_and_timeout_are_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)
    config = EngineConfig(
        engine="native",
        params={"contrast": -9.5, "source_color_index": 99, "timeout": 0},
        timeout=300,
    )

    NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--contrast") == "-1.0"
    assert _argv_value(argv, "--source-color-index") == "4"
    assert calls[0]["kwargs"]["timeout"] == 1


def test_unknown_parameter_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineConfigError, match="unknown parameter"):
        NativeEngine().generate(
            request,
            EngineConfig(engine="native", params={"not_a_parameter": "x"}),
        )

    assert calls == []


@pytest.mark.parametrize("scheme", ["scheme-nope", "scheme-smart"])
def test_invalid_scheme_choice_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scheme: str
) -> None:
    _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineConfigError, match="invalid choice"):
        NativeEngine().generate(
            request,
            EngineConfig(engine="native", params={"scheme_type": scheme}),
        )


def test_timeout_maps_to_engine_execution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_raising_run(
        monkeypatch,
        subprocess.TimeoutExpired(["tpr-native"], 42, stderr="slow"),
    )
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineExecutionError, match="timed out"):
        NativeEngine().generate(request, EngineConfig(engine="native", timeout=42))


def test_non_zero_exit_includes_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_run(monkeypatch, "", returncode=2, stderr="boom")
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineExecutionError, match="boom") as exc_info:
        NativeEngine().generate(request, EngineConfig(engine="native"))

    assert exc_info.value.returncode == 2
    assert exc_info.value.stderr == "boom"


def test_malformed_json_maps_to_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_run(monkeypatch, "{not json")
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineParseError, match="invalid JSON"):
        NativeEngine().generate(request, EngineConfig(engine="native"))


def test_missing_role_maps_to_parse_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload()
    del payload["modes"]["dark"]["roles"]["background"]
    _install_fake_run(monkeypatch, payload)
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineParseError, match="background"):
        NativeEngine().generate(request, EngineConfig(engine="native"))


def test_missing_binary_maps_to_not_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_raising_run(monkeypatch, FileNotFoundError("tpr-native"))
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineNotAvailableError, match="not available"):
        NativeEngine().generate(request, EngineConfig(engine="native"))


def test_is_available_uses_path(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = NativeEngine()

    monkeypatch.setattr(native_module.shutil, "which", lambda _name: None)
    assert engine.is_available() is False
    monkeypatch.setattr(native_module.shutil, "which", lambda _name: "/usr/bin/tpr-native")
    assert engine.is_available() is True


def test_prefer_and_fallback_are_forwarded_for_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, image = _image_request(tmp_path)
    calls = _install_fake_run(monkeypatch, _payload(image))
    config = EngineConfig(
        engine="native",
        params={
            "prefer": "closest-to-fallback",
            "fallback_color": "#AABBCC",
            "source_color_index": 3,
        },
    )

    NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--prefer") == "closest-to-fallback"
    assert _argv_value(argv, "--fallback-color") == "#aabbcc"
    # --prefer takes precedence over --source-color-index in the helper.
    assert "--source-color-index" not in argv


def test_fallback_is_forwarded_without_a_preference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, image = _image_request(tmp_path)
    calls = _install_fake_run(monkeypatch, _payload(image))
    config = EngineConfig(engine="native", params={"fallback_color": "#123456"})

    NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--source-color-index") == "0"
    assert _argv_value(argv, "--fallback-color") == "#123456"
    assert "--prefer" not in argv


def test_color_source_ignores_prefer_and_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="color", color="#ff0000")
    config = EngineConfig(
        engine="native",
        params={"prefer": "darkness", "fallback_color": "#123456"},
    )

    NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert "--prefer" not in argv
    assert "--fallback-color" not in argv
    assert "--source-color-index" not in argv


def test_invalid_fallback_color_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineConfigError, match="fallback_color"):
        NativeEngine().generate(
            request,
            EngineConfig(engine="native", params={"fallback_color": "not-a-color"}),
        )

    assert calls == []


@pytest.mark.parametrize(
    "prefer",
    ["darkness", "lightness", "saturation", "less-saturation", "value", "closest-to-fallback"],
)
def test_every_catalog_preference_is_a_valid_choice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prefer: str
) -> None:
    request, image = _image_request(tmp_path)
    calls = _install_fake_run(monkeypatch, _payload(image))

    NativeEngine().generate(
        request,
        EngineConfig(engine="native", params={"prefer": prefer, "fallback_color": "#000000"}),
    )

    assert _argv_value(calls[0]["argv"], "--prefer") == prefer


def test_unknown_preference_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineConfigError, match="invalid choice"):
        NativeEngine().generate(
            request,
            EngineConfig(engine="native", params={"prefer": "brightest"}),
        )

    assert calls == []


def test_missing_image_is_a_config_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="image", image_path=tmp_path / "absent.png")

    with pytest.raises(EngineConfigError, match="not a file"):
        NativeEngine().generate(request, EngineConfig(engine="native"))

    assert calls == []


def test_lightness_flags_are_forwarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, image = _image_request(tmp_path)
    calls = _install_fake_run(monkeypatch, _payload(image))
    config = EngineConfig(
        engine="native",
        params={"lightness_dark": 0.5, "lightness_light": -0.25},
    )

    NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--lightness-dark") == "0.5"
    assert _argv_value(argv, "--lightness-light") == "-0.25"


def test_lightness_defaults_zero_and_is_forwarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _ = _image_request(tmp_path)
    calls = _install_fake_run(monkeypatch, _payload())

    NativeEngine().generate(request, EngineConfig(engine="native"))

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--lightness-dark") == "0.0"
    assert _argv_value(argv, "--lightness-light") == "0.0"


def test_lightness_extremes_are_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, _ = _image_request(tmp_path)
    calls = _install_fake_run(monkeypatch, _payload())
    config = EngineConfig(
        engine="native",
        params={"lightness_dark": 99.0, "lightness_light": -99.0},
    )

    NativeEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--lightness-dark") == "1.0"
    assert _argv_value(argv, "--lightness-light") == "-1.0"


def test_invalid_lightness_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    for name in ("lightness_dark", "lightness_light"):
        with pytest.raises(EngineConfigError, match=name):
            NativeEngine().generate(
                request, EngineConfig(engine="native", params={name: "abc"})
            )
        with pytest.raises(EngineConfigError, match=name):
            NativeEngine().generate(
                request,
                EngineConfig(engine="native", params={name: float("nan")}),
            )

    assert calls == []
