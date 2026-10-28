from __future__ import annotations

import math

import pytest

from theme_producer.domain.exceptions import (
    InvalidImageMetricsError,
    InvalidSchemePolicyCatalogError,
    InvalidSchemeRuleError,
    UnknownSchemePolicyError,
)
from theme_producer.domain.scheme_policy import (
    Condition,
    ImageMetrics,
    MetricName,
    Operator,
    Rule,
    SchemePolicy,
    SchemePolicyCatalog,
    SchemeVariant,
)
from theme_producer.domain.scheme_policy_resolver import SchemePolicyResolver

METRIC_DEFAULTS: dict[str, float] = {
    "saturation": 0.5,
    "colorfulness": 0.5,
    "lightness": 0.5,
    "contrast": 0.5,
    "hue_diversity": 0.5,
}


def metrics(**overrides: object) -> ImageMetrics:
    fields = {**METRIC_DEFAULTS, **overrides}
    return ImageMetrics(**fields)  # type: ignore[arg-type]


def balanced_policy() -> SchemePolicy:
    """The documented ``balanced`` profile from docs/SCHEME-POLICY.md."""
    return SchemePolicy(
        name="balanced",
        rules=(
            Rule(
                (Condition(MetricName.COLORFULNESS, Operator.LT, 0.08),), SchemeVariant.MONOCHROME
            ),
            Rule((Condition(MetricName.SATURATION, Operator.LT, 0.15),), SchemeVariant.NEUTRAL),
            Rule(
                (
                    Condition(MetricName.COLORFULNESS, Operator.GTE, 0.35),
                    Condition(MetricName.SATURATION, Operator.GTE, 0.55),
                ),
                SchemeVariant.VIBRANT,
            ),
            Rule(
                (Condition(MetricName.HUE_DIVERSITY, Operator.GTE, 0.60),),
                SchemeVariant.EXPRESSIVE,
            ),
        ),
        default=SchemeVariant.TONAL_SPOT,
    )


def resolve_probe(condition: Condition, **overrides: object) -> SchemeVariant:
    policy = SchemePolicy(
        name="probe",
        rules=(Rule((condition,), SchemeVariant.VIBRANT),),
        default=SchemeVariant.NEUTRAL,
    )
    return SchemePolicyResolver.resolve(policy, metrics(**overrides))


def test_variants_are_the_nine_concrete_material_schemes() -> None:
    assert len(SchemeVariant) == 9
    assert "scheme-smart" not in {variant.value for variant in SchemeVariant}


@pytest.mark.parametrize("metric", list(MetricName))
def test_each_metric_name_reads_its_field(metric: MetricName) -> None:
    measured = ImageMetrics(0.1, 0.2, 0.3, 0.4, 0.5)
    expected = {
        MetricName.SATURATION: 0.1,
        MetricName.COLORFULNESS: 0.2,
        MetricName.LIGHTNESS: 0.3,
        MetricName.CONTRAST: 0.4,
        MetricName.HUE_DIVERSITY: 0.5,
    }[metric]

    assert measured.value_for(metric) == pytest.approx(expected)
    assert measured.value_for(metric.value) == pytest.approx(expected)


def test_metric_names_are_the_documented_five() -> None:
    assert {metric.value for metric in MetricName} == {
        "saturation",
        "colorfulness",
        "lightness",
        "contrast",
        "hue_diversity",
    }


def test_image_metrics_accept_and_normalize_the_unit_interval() -> None:
    measured = ImageMetrics(0, 0.25, 0.5, 1, 1.0)

    assert isinstance(measured.saturation, float)
    assert measured.saturation == 0.0
    assert measured.lightness == 0.5
    assert measured.contrast == 1.0


@pytest.mark.parametrize("value", [-0.01, 1.01, math.nan, math.inf, -math.inf, True, "0.5", None])
def test_invalid_image_metrics_are_typed(value: object) -> None:
    with pytest.raises(InvalidImageMetricsError, match="image metric|must be"):
        metrics(saturation=value)


def test_unknown_metric_name_is_typed() -> None:
    with pytest.raises(InvalidImageMetricsError, match="unknown image metric"):
        ImageMetrics(0.5, 0.5, 0.5, 0.5, 0.5).value_for("luminosity")


@pytest.mark.parametrize(
    ("condition", "measured", "expected"),
    [
        (Condition(MetricName.SATURATION, Operator.LT, 0.5), 0.49, True),
        (Condition(MetricName.SATURATION, Operator.LT, 0.5), 0.5, False),
        (Condition(MetricName.SATURATION, Operator.LTE, 0.5), 0.5, True),
        (Condition(MetricName.SATURATION, Operator.LTE, 0.5), 0.51, False),
        (Condition(MetricName.SATURATION, Operator.GT, 0.5), 0.51, True),
        (Condition(MetricName.SATURATION, Operator.GT, 0.5), 0.5, False),
        (Condition(MetricName.SATURATION, Operator.GTE, 0.5), 0.5, True),
        (Condition(MetricName.SATURATION, Operator.GTE, 0.5), 0.49, False),
        (Condition(MetricName.SATURATION, Operator.BETWEEN, 0.2, 0.4), 0.2, True),
        (Condition(MetricName.SATURATION, Operator.BETWEEN, 0.2, 0.4), 0.4, True),
        (Condition(MetricName.SATURATION, Operator.BETWEEN, 0.2, 0.4), 0.19, False),
        (Condition(MetricName.SATURATION, Operator.BETWEEN, 0.2, 0.4), 0.41, False),
    ],
)
def test_every_operator(condition: Condition, measured: float, expected: bool) -> None:
    resolved = resolve_probe(condition, saturation=measured)

    assert resolved is (SchemeVariant.VIBRANT if expected else SchemeVariant.NEUTRAL)


def test_conditions_are_anded() -> None:
    policy = SchemePolicy(
        name="and",
        rules=(
            Rule(
                (
                    Condition(MetricName.SATURATION, Operator.GTE, 0.6),
                    Condition(MetricName.CONTRAST, Operator.GTE, 0.6),
                ),
                SchemeVariant.VIBRANT,
            ),
        ),
        default=SchemeVariant.NEUTRAL,
    )

    assert (
        SchemePolicyResolver.resolve(policy, metrics(saturation=0.8, contrast=0.4))
        is SchemeVariant.NEUTRAL
    )
    assert (
        SchemePolicyResolver.resolve(policy, metrics(saturation=0.4, contrast=0.8))
        is SchemeVariant.NEUTRAL
    )
    assert (
        SchemePolicyResolver.resolve(policy, metrics(saturation=0.8, contrast=0.8))
        is SchemeVariant.VIBRANT
    )


def test_first_matching_rule_wins() -> None:
    policy = SchemePolicy(
        name="ordered",
        rules=(
            Rule((Condition(MetricName.SATURATION, Operator.GTE, 0.1),), SchemeVariant.EXPRESSIVE),
            Rule((Condition(MetricName.SATURATION, Operator.GTE, 0.1),), SchemeVariant.VIBRANT),
        ),
        default=SchemeVariant.NEUTRAL,
    )

    assert SchemePolicyResolver.resolve(policy, metrics(saturation=0.9)) is SchemeVariant.EXPRESSIVE


def test_unmatched_metrics_fall_back_to_the_policy_default() -> None:
    policy = balanced_policy()

    assert (
        SchemePolicyResolver.resolve(
            policy, metrics(saturation=0.4, colorfulness=0.2, hue_diversity=0.2)
        )
        is SchemeVariant.TONAL_SPOT
    )


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"saturation": 0.0, "colorfulness": 0.05}, SchemeVariant.MONOCHROME),
        ({"saturation": 0.1, "colorfulness": 0.2}, SchemeVariant.NEUTRAL),
        ({"saturation": 0.6, "colorfulness": 0.4}, SchemeVariant.VIBRANT),
        ({"saturation": 0.4, "colorfulness": 0.2, "hue_diversity": 0.7}, SchemeVariant.EXPRESSIVE),
        ({"saturation": 0.4, "colorfulness": 0.2, "hue_diversity": 0.3}, SchemeVariant.TONAL_SPOT),
    ],
)
def test_documented_balanced_profile(overrides: dict[str, float], expected: SchemeVariant) -> None:
    assert SchemePolicyResolver.resolve(balanced_policy(), metrics(**overrides)) is expected


def test_resolver_is_static_and_pure() -> None:
    policy = balanced_policy()
    measured = metrics(saturation=0.6, colorfulness=0.4)

    first = SchemePolicyResolver.resolve(policy, measured)
    second = SchemePolicyResolver.resolve(policy, measured)

    assert first is second is SchemeVariant.VIBRANT
    assert policy.rules[0].variant is SchemeVariant.MONOCHROME


def test_resolver_rejects_wrong_types() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="must be a SchemePolicy"):
        SchemePolicyResolver.resolve("balanced", metrics())  # type: ignore[arg-type]
    with pytest.raises(InvalidImageMetricsError, match="must be ImageMetrics"):
        SchemePolicyResolver.resolve(balanced_policy(), object())  # type: ignore[arg-type]


def test_condition_coerces_strings_and_keeps_between_upper() -> None:
    condition = Condition("contrast", "between", 0.2, 0.4)

    assert condition.metric is MetricName.CONTRAST
    assert condition.operator is Operator.BETWEEN
    assert condition.value == 0.2
    assert condition.upper == 0.4


def test_between_requires_an_upper_bound() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="requires an upper bound"):
        Condition(MetricName.CONTRAST, Operator.BETWEEN, 0.2)


def test_between_upper_must_not_be_below_value() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="upper must be >="):
        Condition(MetricName.CONTRAST, Operator.BETWEEN, 0.6, 0.4)

    assert Condition(MetricName.CONTRAST, Operator.BETWEEN, 0.4, 0.4).upper == 0.4


def test_upper_is_only_valid_for_between() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="only valid for the 'between' operator"):
        Condition(MetricName.CONTRAST, Operator.GTE, 0.2, 0.4)


@pytest.mark.parametrize("value", [-0.1, 1.1, math.nan, math.inf, True, "half", None])
def test_invalid_condition_values_are_typed(value: object) -> None:
    with pytest.raises(InvalidSchemeRuleError, match="condition value"):
        Condition(MetricName.CONTRAST, Operator.GTE, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("upper", [-0.1, 1.1, math.nan])
def test_invalid_condition_uppers_are_typed(upper: object) -> None:
    with pytest.raises(InvalidSchemeRuleError, match="condition upper"):
        Condition(MetricName.CONTRAST, Operator.BETWEEN, 0.2, upper)  # type: ignore[arg-type]


def test_unknown_condition_metric_and_operator_are_typed() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="condition metric"):
        Condition("luminosity", Operator.GTE, 0.5)  # type: ignore[arg-type]
    with pytest.raises(InvalidSchemeRuleError, match="condition operator"):
        Condition(MetricName.CONTRAST, "eq", 0.5)  # type: ignore[arg-type]


def test_rule_requires_at_least_one_condition() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="at least one condition"):
        Rule((), SchemeVariant.NEUTRAL)


def test_rule_rejects_non_conditions() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="must all be Condition"):
        Rule(("contrast >= 0.5",), SchemeVariant.NEUTRAL)  # type: ignore[arg-type]


def test_rule_rejects_unknown_variant() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="rule variant"):
        Rule((Condition(MetricName.CONTRAST, Operator.GTE, 0.5),), "scheme-smart")


def test_rule_coerces_list_conditions_and_string_variant() -> None:
    rule = Rule(
        [Condition(MetricName.CONTRAST, Operator.GTE, 0.5)],  # type: ignore[arg-type]
        "scheme-vibrant",
    )

    assert isinstance(rule.conditions, tuple)
    assert rule.variant is SchemeVariant.VIBRANT


def test_policy_requires_a_name_and_rules() -> None:
    with pytest.raises(InvalidSchemeRuleError, match="non-empty string"):
        SchemePolicy(" ", (), SchemeVariant.NEUTRAL)
    with pytest.raises(InvalidSchemeRuleError, match="at least one rule"):
        SchemePolicy("empty", (), SchemeVariant.NEUTRAL)


def test_policy_rejects_unknown_default_variant() -> None:
    rule = Rule((Condition(MetricName.CONTRAST, Operator.GTE, 0.5),), SchemeVariant.NEUTRAL)

    with pytest.raises(InvalidSchemeRuleError, match="default must be one of"):
        SchemePolicy("bad-default", (rule,), "scheme-smart")


def test_policy_normalizes_rules_and_default() -> None:
    policy = SchemePolicy(
        "probe",
        (Rule((Condition(MetricName.CONTRAST, Operator.GTE, 0.5),), "scheme-vibrant"),),
        "scheme-neutral",
    )

    assert isinstance(policy.rules, tuple)
    assert policy.default is SchemeVariant.NEUTRAL


def catalog(**overrides: object) -> SchemePolicyCatalog:
    policy = balanced_policy()
    fields: dict[str, object] = {
        "version": 1,
        "default_policy": "balanced",
        "policies": {"balanced": policy},
    }
    fields.update(overrides)
    return SchemePolicyCatalog(**fields)  # type: ignore[arg-type]


def test_catalog_selects_named_and_default_policies() -> None:
    vivid = SchemePolicy(
        "vivid",
        (Rule((Condition(MetricName.CONTRAST, Operator.GTE, 0.55),), SchemeVariant.VIBRANT),),
        SchemeVariant.VIBRANT,
    )
    catalog_with_vivid = catalog(policies={"balanced": balanced_policy(), "vivid": vivid})

    assert catalog_with_vivid.select() is catalog_with_vivid.policies["balanced"]
    assert catalog_with_vivid.select("vivid") is vivid


def test_catalog_policies_are_immutable() -> None:
    loaded = catalog()

    with pytest.raises(TypeError):
        loaded.policies["vivid"] = balanced_policy()  # type: ignore[index]


@pytest.mark.parametrize("version", [2, 0, "1", True, None])
def test_catalog_rejects_unsupported_or_malformed_versions(version: object) -> None:
    with pytest.raises(InvalidSchemePolicyCatalogError, match="version"):
        catalog(version=version)


def test_catalog_requires_at_least_one_policy() -> None:
    with pytest.raises(InvalidSchemePolicyCatalogError, match="at least one policy"):
        catalog(policies={})


def test_catalog_requires_a_known_default_policy() -> None:
    with pytest.raises(UnknownSchemePolicyError, match="default scheme policy"):
        catalog(default_policy="missing")


def test_catalog_rejects_an_empty_default_name() -> None:
    with pytest.raises(InvalidSchemePolicyCatalogError, match="default_policy"):
        catalog(default_policy=" ")


def test_catalog_rejects_mismatched_policy_names() -> None:
    with pytest.raises(InvalidSchemePolicyCatalogError, match="does not match"):
        catalog(policies={"vivid": balanced_policy()})


def test_catalog_rejects_non_policy_values_and_non_string_keys() -> None:
    with pytest.raises(InvalidSchemePolicyCatalogError, match="must be a SchemePolicy"):
        catalog(policies={"balanced": "balanced"})
    with pytest.raises(InvalidSchemePolicyCatalogError, match="non-empty strings"):
        catalog(policies={1: balanced_policy()})


def test_unknown_policy_selection_is_typed() -> None:
    loaded = catalog()

    with pytest.raises(UnknownSchemePolicyError, match="known policies: balanced"):
        loaded.select("muted")
    with pytest.raises(UnknownSchemePolicyError, match="must be a string"):
        loaded.select(42)  # type: ignore[arg-type]


def test_empty_policy_names_are_rejected_before_lookup() -> None:
    with pytest.raises(UnknownSchemePolicyError, match="unknown scheme policy"):
        catalog().select("")
