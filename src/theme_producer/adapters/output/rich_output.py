"""Rich output adapter for interactive terminals."""

from __future__ import annotations

from cli_output.domain.enums import OutputFormat

from theme_producer.adapters.output import OutputAdapterBase


class RichOutput(OutputAdapterBase):
    _default_format = OutputFormat.RICH
