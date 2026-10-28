"""Pydantic boundary schema for ``scheme-policies.yaml``.

The assembler validates the document's *shape* through these models; the loader
then converts it into the pure domain objects, which validate metric,
operator, and variant vocabulary plus ranges, rules, and defaults. Keeping the
vocabulary checks in the domain means the YAML schema stays a thin, literal
description of the file format.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "SchemePolicyCatalogSchema",
    "SchemePolicySchema",
    "SchemeRuleSchema",
]


class SchemeRuleSchema(BaseModel):
    """One ordered rule: a ``when`` metric map and the selected variant."""

    model_config = ConfigDict(extra="forbid")

    # metric name -> operator -> operand. ``between`` takes ``[lower, upper]``
    # or ``{min, max}``; every other operator takes a single number.
    when: dict[str, dict[str, Any]]
    variant: str


class SchemePolicySchema(BaseModel):
    """One named profile with ordered rules and a fallback variant."""

    model_config = ConfigDict(extra="forbid")

    default: str
    rules: list[SchemeRuleSchema] = Field(default_factory=list)


class SchemePolicyCatalogSchema(BaseModel):
    """The versioned catalog document."""

    model_config = ConfigDict(extra="forbid")

    version: int
    default: str
    policies: dict[str, SchemePolicySchema] = Field(default_factory=dict)
