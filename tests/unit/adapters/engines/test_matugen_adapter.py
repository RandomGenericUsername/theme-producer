from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import theme_producer.adapters.engines.matugen as matugen_module
from theme_producer.adapters.engines.matugen import MatugenEngine
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.enums import MaterialRole, ModeName, PaletteName, SourceKind
from theme_producer.domain.exceptions import (
    EngineConfigError,
    EngineExecutionError,
    EngineNotAvailableError,
    EngineParseError,
)

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "matugen.json"
CONFIG_TEXT = "[config]\n\n[templates]\n"


@pytest.fixture(autouse=True)
def _force_fallback_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests off the host binary and its version call."""
    monkeypatch.setattr(matugen_module.shutil, "which", lambda _name: None)
    matugen_module._engine_version.cache_clear()
    yield
    matugen_module._engine_version.cache_clear()


def _payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _install_fake_run(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any] | str,
    *,
    returncode: int = 0,
    stderr: str = "",
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        config_text = None
        if "--config" in argv:
            config_text = Path(argv[argv.index("--config") + 1]).read_text(encoding="utf-8")
        calls.append({"argv": list(argv), "kwargs": kwargs, "config_text": config_text})
        stdout = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(matugen_module.subprocess, "run", fake_run)
    return calls


def _install_raising_run(
    monkeypatch: pytest.MonkeyPatch,
    exc: BaseException,
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        raise exc

    monkeypatch.setattr(matugen_module.subprocess, "run", fake_run)
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
    calls = _install_fake_run(monkeypatch, _payload())
    request, image = _image_request(tmp_path)
    config = EngineConfig(
        engine="matugen",
        params={
            "mode": "light",
            "scheme_type": "scheme-vibrant",
            "contrast": 0.5,
            "source_color_index": 2,
        },
        timeout=42,
    )

    theme = MatugenEngine().generate(request, config)

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
    assert theme.generator.engine == "matugen"
    assert theme.generator.engine_version == "4.2.0"
    assert theme.generator.schema_version == "1"

    assert len(calls) == 1
    call = calls[0]
    argv = call["argv"]
    assert argv[0] == "matugen"
    assert argv[1] == "image"
    assert argv[2] == str(image.resolve())
    assert _argv_value(argv, "--json") == "hex"
    assert "--dry-run" in argv
    assert _argv_value(argv, "--mode") == "light"
    assert _argv_value(argv, "--type") == "scheme-vibrant"
    assert _argv_value(argv, "--contrast") == "0.5"
    assert _argv_value(argv, "--source-color-index") == "2"
    assert _argv_value(argv, "--base16-backend") == "wal"
    assert _argv_value(argv, "--config").startswith("/")
    assert argv[-1] == "--quiet"
    assert call["config_text"] == CONFIG_TEXT
    assert call["kwargs"]["shell"] is False
    assert call["kwargs"]["timeout"] == 42
    assert call["kwargs"]["capture_output"] is True
    assert call["kwargs"]["text"] is True


def test_color_source_argv_and_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="color", color="#FF0000")
    config = EngineConfig(engine="matugen", params={}, timeout=10)

    theme = MatugenEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert argv[1:4] == ["color", "hex", "#ff0000"]
    assert "--source-color-index" not in argv
    assert "--base16-backend" not in argv
    assert _argv_value(argv, "--json") == "hex"
    assert "--dry-run" in argv
    assert argv[-1] == "--quiet"

    assert theme.source.kind is SourceKind.COLOR
    assert theme.source.path is None
    assert theme.source.hash == sha256(b"#FF0000").hexdigest()


def test_json_source_is_rejected_before_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="json", json_path=tmp_path / "theme.json")

    with pytest.raises(EngineConfigError, match="json source"):
        MatugenEngine().generate(request, EngineConfig(engine="matugen"))

    assert calls == []


def test_contrast_index_and_timeout_are_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)
    config = EngineConfig(
        engine="matugen",
        params={"contrast": 9.5, "source_color_index": 99, "timeout": 0},
        timeout=300,
    )

    MatugenEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--contrast") == "1.0"
    assert _argv_value(argv, "--source-color-index") == "3"
    assert calls[0]["kwargs"]["timeout"] == 1


def test_eight_digit_hex_alpha_is_stripped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload()
    payload["colors"]["background"]["dark"]["color"] = "#11223344"
    payload["colors"]["background"]["light"]["color"] = "#aabbccdd"
    payload["palettes"]["primary"]["40"]["color"] = "#01020380"
    _install_fake_run(monkeypatch, payload)
    request, _ = _image_request(tmp_path)

    theme = MatugenEngine().generate(request, EngineConfig(engine="matugen"))

    assert theme.dark.roles[MaterialRole.BACKGROUND].hex == "#112233"
    assert theme.light.roles[MaterialRole.BACKGROUND].hex == "#aabbcc"
    assert theme.dark.palettes[PaletteName.PRIMARY].tones[40].hex == "#010203"
    assert theme.light.palettes[PaletteName.PRIMARY].tones[40].hex == "#010203"


def test_timeout_maps_to_engine_execution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_raising_run(
        monkeypatch,
        subprocess.TimeoutExpired(["matugen"], 42, stderr="slow"),
    )
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineExecutionError, match="timed out"):
        MatugenEngine().generate(request, EngineConfig(engine="matugen", timeout=42))


def test_non_zero_exit_includes_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_run(monkeypatch, "", returncode=2, stderr="boom")
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineExecutionError, match="boom") as exc_info:
        MatugenEngine().generate(request, EngineConfig(engine="matugen"))

    assert exc_info.value.returncode == 2
    assert exc_info.value.stderr == "boom"


def test_malformed_json_maps_to_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_run(monkeypatch, "{not json")
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineParseError, match="invalid JSON"):
        MatugenEngine().generate(request, EngineConfig(engine="matugen"))


def test_missing_role_maps_to_parse_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload()
    del payload["colors"]["background"]
    _install_fake_run(monkeypatch, payload)
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineParseError, match="background"):
        MatugenEngine().generate(request, EngineConfig(engine="matugen"))


def test_missing_binary_maps_to_not_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_raising_run(monkeypatch, FileNotFoundError("matugen"))
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineNotAvailableError, match="not available"):
        MatugenEngine().generate(request, EngineConfig(engine="matugen"))


def test_is_available_uses_path(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = MatugenEngine()

    assert engine.is_available() is False
    monkeypatch.setattr(matugen_module.shutil, "which", lambda _name: "/usr/bin/matugen")
    assert engine.is_available() is True


def test_prefer_and_fallback_are_forwarded_for_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)
    config = EngineConfig(
        engine="matugen",
        params={
            "prefer": "lightness",
            "fallback_color": "#AABBCC",
            "source_color_index": 2,
        },
    )

    MatugenEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--prefer") == "lightness"
    assert _argv_value(argv, "--fallback-color") == "#aabbcc"
    # matugen gives the explicit index precedence, so only forward one.
    assert "--source-color-index" not in argv
    assert _argv_value(argv, "--base16-backend") == "wal"


def test_fallback_is_forwarded_without_a_preference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)
    config = EngineConfig(engine="matugen", params={"fallback_color": "#123456"})

    MatugenEngine().generate(request, config)

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
        engine="matugen",
        params={"prefer": "darkness", "fallback_color": "#123456"},
    )

    MatugenEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert argv[1:4] == ["color", "hex", "#ff0000"]
    assert "--prefer" not in argv
    assert "--fallback-color" not in argv
    assert "--source-color-index" not in argv


def test_invalid_fallback_color_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineConfigError, match="fallback_color"):
        MatugenEngine().generate(
            request,
            EngineConfig(engine="matugen", params={"fallback_color": "#12345"}),
        )

    assert calls == []


def test_unknown_preference_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)

    with pytest.raises(EngineConfigError, match="invalid choice"):
        MatugenEngine().generate(
            request,
            EngineConfig(engine="matugen", params={"prefer": "brightest"}),
        )

    assert calls == []


def test_missing_image_is_a_config_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="image", image_path=tmp_path / "absent.png")

    with pytest.raises(EngineConfigError, match="not a file"):
        MatugenEngine().generate(request, EngineConfig(engine="matugen"))

    assert calls == []


def test_lightness_flags_are_forwarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)
    config = EngineConfig(
        engine="matugen",
        params={"lightness_dark": 0.5, "lightness_light": -0.25},
    )

    MatugenEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert _argv_value(argv, "--lightness-dark") == "0.5"
    assert _argv_value(argv, "--lightness-light") == "-0.25"


def test_lightness_flags_are_forwarded_for_color_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request = ThemeRequest(source_kind="color", color="#ff0000")
    config = EngineConfig(
        engine="matugen",
        params={"lightness_dark": 0.5, "lightness_light": 0.25},
    )

    MatugenEngine().generate(request, config)

    argv = calls[0]["argv"]
    assert argv[1:4] == ["color", "hex", "#ff0000"]
    assert _argv_value(argv, "--lightness-dark") == "0.5"
    assert _argv_value(argv, "--lightness-light") == "0.25"


def test_lightness_extremes_are_clamped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _install_fake_run(monkeypatch, _payload())
    request, _ = _image_request(tmp_path)
    config = EngineConfig(
        engine="matugen",
        params={"lightness_dark": 99.0, "lightness_light": -99.0},
    )

    MatugenEngine().generate(request, config)

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
            MatugenEngine().generate(
                request, EngineConfig(engine="matugen", params={name: "abc"})
            )
        with pytest.raises(EngineConfigError, match=name):
            MatugenEngine().generate(
                request,
                EngineConfig(engine="matugen", params={name: float("nan")}),
            )

    assert calls == []
