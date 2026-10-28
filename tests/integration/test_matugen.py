"""End-to-end matugen adapter test against the real binary.

Skipped with a clear reason when matugen is not installed: engine-dependent
tests are never silently absent. The test runs without a TTY, which is the
non-interactive proof AD-3 requires.
"""

from __future__ import annotations

import shutil
import struct
import zlib
from pathlib import Path

import pytest

from theme_producer.adapters.engines.matugen import MatugenEngine
from theme_producer.domain.engines import EngineConfig, ThemeRequest
from theme_producer.domain.enums import SourceKind
from theme_producer.domain.models import Theme

_MATUGEN = shutil.which("matugen")

pytestmark = pytest.mark.skipif(
    _MATUGEN is None,
    reason="matugen 4.2.0 is not on PATH; run this test in the pinned engine image",
)


def _write_png(path: Path, width: int = 16, height: int = 16) -> Path:
    """Write a minimal solid-color PNG using only the standard library."""
    pixel = bytes((0x2E, 0x7D, 0x32))
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


def test_matugen_generates_a_valid_theme_non_interactively(tmp_path: Path) -> None:
    image = _write_png(tmp_path / "seed.png")
    request = ThemeRequest(source_kind=SourceKind.IMAGE, image_path=image)
    config = EngineConfig(engine="matugen", params={"timeout": 120}, timeout=120)

    theme = MatugenEngine().generate(request, config)

    assert isinstance(theme, Theme)
    assert theme.source.kind is SourceKind.IMAGE
    assert theme.source.path == str(image.resolve())
    assert theme.source.hash is not None and len(theme.source.hash) == 64
    assert len(theme.dark.roles) == 50
    assert len(theme.light.roles) == 50
    assert len(theme.dark.palettes) == 6
    assert len(theme.light.palettes) == 6
    assert all(len(palette.tones) == 18 for palette in theme.dark.palettes.values())
    assert all(len(palette.tones) == 18 for palette in theme.light.palettes.values())
    assert theme.generator.engine == "matugen"
    assert theme.generator.engine_version
    assert theme.generator.schema_version == "1"
    assert theme.scheme == "scheme-tonal-spot"
