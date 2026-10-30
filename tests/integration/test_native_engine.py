"""End-to-end native engine test against the real `tpr-native` binary.

Skipped with a clear reason when the helper is not built or not on PATH. The
32x32 PNG is written with only the standard library, so the test exercises the
real image path without adding an image dependency to the test suite.
"""

from __future__ import annotations

import shutil
import struct
import zlib
from hashlib import sha256
from pathlib import Path

import jsonschema
import pytest

from theme_producer.adapters.engines.native import NativeEngine
from theme_producer.adapters.theme_json import load_theme_schema
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.enums import SourceKind

_NATIVE = shutil.which("tpr-native")

pytestmark = pytest.mark.skipif(
    _NATIVE is None,
    reason=(
        "tpr-native is not on PATH; build native/ "
        "(`cd native && cargo build --release --locked`) and add "
        "`native/target/release` to PATH, or run in the pinned native image"
    ),
)

_SCHEMA = load_theme_schema()


def _write_png(path: Path, width: int = 32, height: int = 32) -> Path:
    """Write a minimal solid-color PNG using only the standard library."""
    pixel = bytes((0x3A, 0x7B, 0xD5))
    raw = b"".join(b"\x00" + pixel * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return path


def test_native_generates_a_schema_valid_theme_from_a_png(tmp_path: Path) -> None:
    image = _write_png(tmp_path / "seed.png")
    request = ThemeRequest(source_kind=SourceKind.IMAGE, image_path=image)
    config = EngineConfig(engine="native", params={"timeout": 120}, timeout=120)

    theme = NativeEngine().generate(request, config)
    payload = theme.to_dict()

    jsonschema.Draft7Validator.check_schema(_SCHEMA)
    jsonschema.validate(instance=payload, schema=_SCHEMA)

    assert theme.source.kind is SourceKind.IMAGE
    assert theme.source.path == str(image.resolve())
    assert theme.source.hash == sha256(image.read_bytes()).hexdigest()
    assert len(theme.dark.roles) == 50
    assert len(theme.light.roles) == 50
    assert len(theme.dark.palettes) == 6
    assert len(theme.light.palettes) == 6
    assert all(len(palette.tones) == 18 for palette in theme.dark.palettes.values())
    assert all(len(palette.tones) == 18 for palette in theme.light.palettes.values())
    assert theme.generator.engine == "native"
    assert theme.generator.engine_version == "0.1.0"
    assert theme.generator.schema_version == "1.1"
    assert theme.scheme == "scheme-tonal-spot"
    assert theme.contrast == 0.0
