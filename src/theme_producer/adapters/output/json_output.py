"""JSON output adapter (the machine contract and CLI default)."""

from __future__ import annotations

from cli_output.domain.enums import OutputFormat

from theme_producer.adapters.output import OutputAdapterBase


class JsonOutput(OutputAdapterBase):
    _default_format = OutputFormat.JSON
