from backend.app.models.economics import CompanyAssumptions, EconomicScenarioInput
from backend.app.models.intelligence import EffectiveTerm
from backend.app.models.stress import (
    DealHealthConfig,
    DealHealthSummary,
    ScenarioAssumptionSource,
    ScenarioSourceLabel,
    ScenarioStressResult,
    StressScenario,
    StressTestResponse,
)
from backend.app.simulation.economics import evaluate_financial_scenario


def run_stress_test(
    terms: list[EffectiveTerm],
    assumptions: CompanyAssumptions,
    expected_usage_units: float,
    expected_usage_revenue: float,
    health_config: DealHealthConfig | None = None,
) -> StressTestResponse:
    config = health_config or DealHealthConfig(target_margin_percent=assumptions.minimum_acceptable_gross_margin)
    scenarios = generate_stress_scenarios(terms, assumptions, expected_usage_units, expected_usage_revenue)
    results = []
    for scenario in scenarios:
        economics = evaluate_financial_scenario(terms, assumptions, scenario.economics_input)
        results.append(
            ScenarioStressResult(
                scenario=scenario,
                economics=economics,
                status=_scenario_status(economics.gross_margin_percent, config),
            )
        )

    return StressTestResponse(health=_summarize_health(results, config), scenarios=results)


def generate_stress_scenarios(
    terms: list[EffectiveTerm],
    assumptions: CompanyAssumptions,
    expected_usage_units: float,
    expected_usage_revenue: float,
) -> list[StressScenario]:
    term_map = {term.field_name: term for term in terms}
    support_hours = assumptions.typical_support_consumption_hours

    return [
        _scenario(
            "Conservative adoption",
            "Customer adoption trails the plan while fixed service obligations remain.",
            0.65,
            support_hours * 0.9,
            1.0,
            0,
            "temporary discounts active",
            99.9,
            -0.1,
            ["lower ramp than sales forecast"],
            expected_usage_units,
            expected_usage_revenue,
            [source("usage_multiplier", ScenarioSourceLabel.system_default, "Default downside adoption factor.")],
        ),
        _scenario(
            "Expected adoption",
            "Commercial model follows the user-entered planning case.",
            1.0,
            support_hours,
            1.0,
            0,
            "contracted discounts active",
            99.9,
            0.0,
            ["baseline planning case"],
            expected_usage_units,
            expected_usage_revenue,
            [source("expected_usage_units", ScenarioSourceLabel.user_entered_assumption, "Entered by the user.")],
        ),
        _scenario(
            "High adoption",
            "Usage exceeds plan and tests overage economics or payment caps.",
            1.5,
            support_hours * 1.15,
            1.0,
            0,
            "contracted discounts active",
            99.9,
            0.25,
            _cap_events(term_map, ["usage exceeds baseline"]),
            expected_usage_units,
            expected_usage_revenue,
            [source("usage_multiplier", ScenarioSourceLabel.synthetic_historical_benchmark, "Synthetic benchmark for strong enterprise expansion.")],
        ),
        _scenario(
            "Support-heavy customer",
            "Support consumption runs materially above the operating plan.",
            1.0,
            support_hours * 2.0,
            1.0,
            0,
            "contracted discounts active",
            99.7,
            0.0,
            _support_events(term_map, ["support demand doubles"]),
            expected_usage_units,
            expected_usage_revenue,
            [source("support_hours", ScenarioSourceLabel.contract_derived if _has_unlimited_support(term_map) else ScenarioSourceLabel.system_default, "Triggered by support obligations or default stress coverage.")],
        ),
        _scenario(
            "Infrastructure-cost increase",
            "Cloud/API unit economics worsen while customer pricing remains unchanged.",
            1.0,
            support_hours,
            1.35,
            0,
            "contracted discounts active",
            99.9,
            0.0,
            ["vendor, cloud, or API serving cost shock"],
            expected_usage_units,
            expected_usage_revenue,
            [source("cost_multiplier", ScenarioSourceLabel.synthetic_historical_benchmark, "Synthetic benchmark for infrastructure volatility.")],
        ),
        _scenario(
            "Renewal",
            "The deal enters its next renewal year using effective escalation terms.",
            1.05,
            support_hours * 1.05,
            1.08,
            1,
            "renewal pricing applies",
            99.9,
            0.05,
            ["renewal escalation or waiver evaluated"],
            expected_usage_units,
            expected_usage_revenue,
            [source("renewal_year", ScenarioSourceLabel.contract_derived, "Derived from renewal escalation terms.")],
        ),
        _scenario(
            "Discount expiry",
            "Temporary introductory discount expires after the initial period.",
            1.0,
            support_hours,
            1.0,
            0,
            "temporary discount expired",
            99.9,
            0.0,
            ["introductory discount removed"],
            expected_usage_units,
            expected_usage_revenue,
            [source("discount_state", ScenarioSourceLabel.contract_derived, "Uses introductory discount terms when present.")],
            apply_temporary_discount=False,
        ),
        _scenario(
            "SLA degradation",
            "Service performance falls below target and credits are applied.",
            1.0,
            support_hours * 1.25,
            1.12,
            0,
            "contracted discounts active",
            98.5,
            0.0,
            ["service credits applied"],
            expected_usage_units,
            expected_usage_revenue,
            [source("sla_performance", ScenarioSourceLabel.contract_derived, "Tests service credit exposure when SLA terms exist.")],
            apply_service_credits=True,
        ),
        _scenario(
            "High adoption + high support",
            "Usage expands while support intensity rises at the same time.",
            1.6,
            support_hours * 1.8,
            1.15,
            0,
            "contracted discounts active",
            99.5,
            0.3,
            _cap_events(term_map, ["expansion creates support load"]),
            expected_usage_units,
            expected_usage_revenue,
            [source("combined_stress", ScenarioSourceLabel.ai_proposed_hypothetical, "Contract-specific combined stress hypothesis.")],
            apply_service_credits=True,
        ),
        _scenario(
            "Downside commercial scenario",
            "Adoption underperforms while cost, support, credits, and rebates move against the deal.",
            0.75,
            support_hours * 1.75,
            1.3,
            0,
            "discounts and concessions active",
            98.0,
            -0.15,
            ["low adoption", "higher servicing load", "credits and rebates applied"],
            expected_usage_units,
            expected_usage_revenue,
            [source("combined_variables", ScenarioSourceLabel.system_default, "Required MVP downside scenario.")],
            apply_service_credits=True,
        ),
    ]


def source(variable: str, label: ScenarioSourceLabel, detail: str) -> ScenarioAssumptionSource:
    return ScenarioAssumptionSource(variable=variable, label=label, detail=detail)


def _scenario(
    name: str,
    description: str,
    usage_multiplier: float,
    support_hours: float,
    cost_multiplier: float,
    renewal_year: int,
    discount_state: str,
    sla_performance_percent: float,
    customer_growth_rate: float,
    events: list[str],
    expected_usage_units: float,
    expected_usage_revenue: float,
    sources: list[ScenarioAssumptionSource],
    apply_temporary_discount: bool = True,
    apply_service_credits: bool = False,
) -> StressScenario:
    return StressScenario(
        name=name,
        description=description,
        usage_multiplier=usage_multiplier,
        support_hours=round(support_hours, 2),
        cost_multiplier=cost_multiplier,
        renewal_year=renewal_year,
        discount_state=discount_state,
        sla_performance_percent=sla_performance_percent,
        customer_growth_rate=customer_growth_rate,
        relevant_commercial_events=events,
        sources=sources,
        economics_input=EconomicScenarioInput(
            name=name,
            expected_usage_units=round(expected_usage_units * usage_multiplier, 2),
            usage_revenue=round(expected_usage_revenue * usage_multiplier, 2),
            support_hours=round(support_hours, 2),
            cost_multiplier=cost_multiplier,
            apply_temporary_discount=apply_temporary_discount,
            apply_service_credits=apply_service_credits,
            apply_rebates=True,
            renewal_number=renewal_year,
        ),
    )


def _summarize_health(results: list[ScenarioStressResult], config: DealHealthConfig) -> DealHealthSummary:
    margins = [result.economics.gross_margin_percent for result in results]
    pass_rate = sum(margin >= config.target_margin_percent for margin in margins) / len(margins) if margins else 0
    expected_margin = _margin_for(results, "Expected adoption", margins[0] if margins else 0)
    downside_margin = _margin_for(results, "Downside commercial scenario", min(margins) if margins else 0)
    worst_margin = min(margins) if margins else 0
    critical = sum(1 for result in results if result.status == "critical")
    warnings = sum(1 for result in results if result.status == "warning")

    return DealHealthSummary(
        rating=_rating(pass_rate, critical, worst_margin, config),
        percentage_above_target_margin=round(pass_rate * 100, 2),
        expected_scenario_margin=round(expected_margin, 2),
        downside_margin=round(downside_margin, 2),
        worst_case_margin=round(worst_margin, 2),
        estimated_annual_exposure=round(sum(result.economics.downside_exposure for result in results), 2),
        critical_scenarios=critical,
        warning_scenarios=warnings,
        calculation_config=config,
    )


def _scenario_status(margin: float, config: DealHealthConfig) -> str:
    gap = config.target_margin_percent - margin
    if gap >= config.critical_margin_gap_percent:
        return "critical"
    if gap > 0:
        return "warning"
    return "pass"


def _rating(pass_rate: float, critical: int, worst_margin: float, config: DealHealthConfig) -> str:
    warning_floor = config.target_margin_percent - config.warning_margin_gap_percent
    if pass_rate >= config.healthy_min_pass_rate and critical == 0 and worst_margin >= warning_floor:
        return "Healthy"
    if pass_rate >= config.mostly_healthy_min_pass_rate and critical <= 1:
        return "Mostly Healthy"
    if pass_rate >= config.fragile_min_pass_rate:
        return "Commercially Fragile"
    return "High Risk"


def _margin_for(results: list[ScenarioStressResult], scenario_name: str, default: float) -> float:
    return next(
        (result.economics.gross_margin_percent for result in results if result.scenario.name == scenario_name),
        default,
    )


def _has_unlimited_support(term_map: dict[str, EffectiveTerm]) -> bool:
    return any(
        term and "unlimited support" in term.normalized_value.lower()
        for term in [
            term_map.get("support_allowance"),
            term_map.get("support_pricing"),
            term_map.get("unusual_custom_commercial_clauses"),
        ]
    )


def _cap_events(term_map: dict[str, EffectiveTerm], defaults: list[str]) -> list[str]:
    cap = term_map.get("maximum_usage_payment_cap")
    if cap and cap.normalized_value != "unknown":
        return defaults + ["payment cap may constrain upside"]
    return defaults


def _support_events(term_map: dict[str, EffectiveTerm], defaults: list[str]) -> list[str]:
    if _has_unlimited_support(term_map):
        return defaults + ["unlimited support clause detected"]
    return defaults
