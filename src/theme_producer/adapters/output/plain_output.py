"""Plain-text output adapter (no ANSI, no tables)."""

from __future__ import annotations

from cli_output.domain.enums import OutputFormat

from theme_producer.adapters.output import OutputAdapterBase


class PlainOutput(OutputAdapterBase):
    _default_format = OutputFormat.PLAIN
