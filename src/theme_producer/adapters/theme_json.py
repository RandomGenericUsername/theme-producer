"""Write the canonical ``theme.json`` artifact.

The writer is the only place that serializes a Theme to disk. It validates the
payload through the domain model's canonical ``from_dict``/``to_dict`` round
trip before writing, so a missing role, palette, or tone can never produce a
file. The committed draft-07 schema is the public contract and is exercised by
the schema tests.
"""

from __future__ import annotations

import json
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any

from theme_producer.domain.exceptions import ThemeValidationError
from theme_producer.domain.models import Theme

__all__ = [
    "THEME_FILENAME",
    "ThemeJsonWriter",
    "load_theme_schema",
    "theme_schema_path",
    "validate_theme_payload",
]

THEME_FILENAME = "theme.json"


def theme_schema_path() -> Path:
    """Return the path to the committed canonical JSON Schema."""
    return Path(resource_files("theme_producer") / "schemas" / "theme.schema.json")


def load_theme_schema() -> dict[str, Any]:
    """Load the committed canonical JSON Schema as a plain mapping."""
    payload = json.loads(theme_schema_path().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ThemeValidationError("theme schema must be a JSON object")
    return payload


def validate_theme_payload(payload: dict[str, Any]) -> None:
    """Validate a canonical payload through the domain model.

    This is stricter than a shape-only check for the properties that matter to
    projections: exactly 50 roles, six palettes, and 18 canonical tones per
    palette in each mode.
    """
    if not isinstance(payload, dict):
        raise ThemeValidationError(f"theme payload must be a mapping; got {type(payload)!r}")
    round_tripped = Theme.from_dict(payload)
    if round_tripped.to_dict() != payload:
        raise ThemeValidationError(
            "theme payload is not canonical after a from_dict/to_dict round trip"
        )


class ThemeJsonWriter:
    """Serialize a Theme to ``theme.json`` after validating its canonical shape."""

    def write(self, theme: Theme, output_dir: Path) -> Path:
        """Write ``theme.json`` into ``output_dir`` and return the written path."""
        if not isinstance(theme, Theme):
            raise TypeError(f"expected Theme, got {type(theme).__name__}")
        payload = theme.to_dict()
        validate_theme_payload(payload)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
        output_path = output_dir / THEME_FILENAME
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path
