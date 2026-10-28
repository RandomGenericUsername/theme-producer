"""Pure scheme-policy resolution: ordered rules, ANDed conditions, first match.

The resolver is deliberately stateless. It never reads a catalog file or an
image; callers load the policy through ``SchemePolicyCatalogPort``, measure the
source through ``ImageMetricsPort``, and then ask this domain service for the
concrete variant.
"""

from __future__ import annotations

from theme_producer.domain.exceptions import (
    InvalidImageMetricsError,
    InvalidSchemeRuleError,
)
from theme_producer.domain.scheme_policy import (
    Condition,
    ImageMetrics,
    Operator,
    SchemePolicy,
    SchemeVariant,
)

__all__ = ["SchemePolicyResolver"]


class SchemePolicyResolver:
    """Resolve a policy and measured metrics to one concrete variant."""

    @staticmethod
    def resolve(policy: SchemePolicy, metrics: ImageMetrics) -> SchemeVariant:
        """Return the variant of the first matching rule, else ``policy.default``.

        Rules are evaluated in order. A rule matches when every one of its
        conditions holds (AND); there is no OR or negation.
        """
        if not isinstance(policy, SchemePolicy):
            raise InvalidSchemeRuleError(f"scheme policy must be a SchemePolicy; got {policy!r}")
        if not isinstance(metrics, ImageMetrics):
            raise InvalidImageMetricsError(
                f"scheme policy metrics must be ImageMetrics; got {metrics!r}"
            )

        for rule in policy.rules:
            if all(
                SchemePolicyResolver._condition_matches(condition, metrics)
                for condition in rule.conditions
            ):
                return rule.variant
        return policy.default

    @staticmethod
    def _condition_matches(condition: Condition, metrics: ImageMetrics) -> bool:
        measured = metrics.value_for(condition.metric)
        operator = condition.operator
        if operator is Operator.LT:
            return measured < condition.value
        if operator is Operator.LTE:
            return measured <= condition.value
        if operator is Operator.GT:
            return measured > condition.value
        if operator is Operator.GTE:
            return measured >= condition.value
        if operator is Operator.BETWEEN:
            if condition.upper is None:
                raise InvalidSchemeRuleError("condition operator 'between' requires an upper bound")
            return condition.value <= measured <= condition.upper
        raise InvalidSchemeRuleError(f"unsupported condition operator {operator!r}")
