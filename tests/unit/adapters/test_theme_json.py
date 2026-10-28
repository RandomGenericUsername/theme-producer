from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from theme_producer.adapters.theme_json import (
    THEME_FILENAME,
    ThemeJsonWriter,
    load_theme_schema,
    theme_schema_path,
    validate_theme_payload,
)
from theme_producer.domain.enums import TONE_ORDER, MaterialRole, PaletteName
from theme_producer.domain.exceptions import ThemeValidationError
from theme_producer.domain.models import Theme

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "theme.json"
SCHEMA = load_theme_schema()


def load_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_theme() -> Theme:
    return Theme.from_dict(load_payload())


def test_schema_is_committed_draft_07() -> None:
    assert theme_schema_path().is_file()
    assert SCHEMA["$schema"] == "http://json-schema.org/draft-07/schema#"
    jsonschema.Draft7Validator.check_schema(SCHEMA)


def test_fixture_validates_against_committed_schema() -> None:
    jsonschema.validate(instance=load_payload(), schema=SCHEMA)


def test_schema_pins_schema_version_and_closed_objects() -> None:
    assert SCHEMA["properties"]["schema_version"]["const"] == "1"
    assert SCHEMA["additionalProperties"] is False
    mode = SCHEMA["definitions"]["mode"]
    assert mode["additionalProperties"] is False
    assert set(mode["properties"]["roles"]["required"]) == {role.value for role in MaterialRole}
    assert set(mode["properties"]["palettes"]["required"]) == {name.value for name in PaletteName}
    palette = SCHEMA["definitions"]["palette"]
    assert palette["additionalProperties"] is False
    assert set(palette["required"]) == {str(tone) for tone in TONE_ORDER}


def test_writer_writes_the_canonical_fixture_bytes(tmp_path: Path) -> None:
    output = ThemeJsonWriter().write(load_theme(), tmp_path)

    assert output == tmp_path / THEME_FILENAME
    assert output.read_text(encoding="utf-8") == FIXTURE.read_text(encoding="utf-8")


def test_written_theme_validates_against_committed_schema(tmp_path: Path) -> None:
    output = ThemeJsonWriter().write(load_theme(), tmp_path)

    jsonschema.validate(instance=json.loads(output.read_text()), schema=SCHEMA)


def test_validate_theme_payload_accepts_fixture() -> None:
    validate_theme_payload(load_payload())


def test_validate_theme_payload_rejects_noncanonical_extras() -> None:
    payload = load_payload()
    payload["extra"] = "not part of the contract"

    with pytest.raises(ThemeValidationError, match="not canonical"):
        validate_theme_payload(payload)


def test_missing_role_fails_schema() -> None:
    payload = copy.deepcopy(load_payload())
    del payload["modes"]["dark"]["roles"]["surface"]

    with pytest.raises(jsonschema.ValidationError, match="surface"):
        jsonschema.validate(instance=payload, schema=SCHEMA)


def test_missing_palette_fails_schema() -> None:
    payload = copy.deepcopy(load_payload())
    del payload["modes"]["light"]["palettes"]["error"]

    with pytest.raises(jsonschema.ValidationError, match="error"):
        jsonschema.validate(instance=payload, schema=SCHEMA)


def test_missing_tone_fails_schema() -> None:
    payload = copy.deepcopy(load_payload())
    del payload["modes"]["dark"]["palettes"]["primary"]["50"]

    with pytest.raises(jsonschema.ValidationError, match="50"):
        jsonschema.validate(instance=payload, schema=SCHEMA)


def test_extra_role_fails_schema() -> None:
    payload = copy.deepcopy(load_payload())
    payload["modes"]["light"]["roles"]["not_a_role"] = "#000000"

    with pytest.raises(jsonschema.ValidationError, match="not_a_role"):
        jsonschema.validate(instance=payload, schema=SCHEMA)


def test_unknown_top_level_key_fails_schema() -> None:
    payload = copy.deepcopy(load_payload())
    payload["schema_version_extra"] = "1"

    with pytest.raises(jsonschema.ValidationError, match="schema_version_extra"):
        jsonschema.validate(instance=payload, schema=SCHEMA)
