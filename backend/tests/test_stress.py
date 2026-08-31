from backend.app.models.economics import CompanyAssumptions
from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus
from backend.app.models.stress import ScenarioSourceLabel
from backend.app.simulation.stress import generate_stress_scenarios, run_stress_test


def test_generates_required_default_scenarios_with_sources():
    scenarios = generate_stress_scenarios(terms(), assumptions(), 1_200_000, 240_000)

    assert [scenario.name for scenario in scenarios] == [
        "Conservative adoption",
        "Expected adoption",
        "High adoption",
        "Support-heavy customer",
        "Infrastructure-cost increase",
        "Renewal",
        "Discount expiry",
        "SLA degradation",
        "High adoption + high support",
        "Downside commercial scenario",
    ]
    assert all(scenario.sources for scenario in scenarios)
    assert scenarios[4].cost_multiplier == 1.35
    assert scenarios[5].renewal_year == 1
    assert scenarios[7].economics_input.apply_service_credits is True


def test_contract_specific_support_and_cap_events_are_added():
    scenario_map = {scenario.name: scenario for scenario in generate_stress_scenarios(terms(include_support_cap=True), assumptions(), 1_200_000, 240_000)}

    assert "unlimited support clause detected" in scenario_map["Support-heavy customer"].relevant_commercial_events
    assert "payment cap may constrain upside" in scenario_map["High adoption"].relevant_commercial_events
    assert scenario_map["Support-heavy customer"].sources[0].label == ScenarioSourceLabel.contract_derived


def test_stress_test_evaluates_all_scenarios_and_summarizes_health():
    response = run_stress_test(terms(), assumptions(), 1_200_000, 240_000)

    assert len(response.scenarios) == 10
    assert response.failure_modes
    assert response.failure_modes[0].financial_impact >= response.failure_modes[-1].financial_impact
    assert response.health.rating in {"Healthy", "Mostly Healthy", "Commercially Fragile", "High Risk"}
    assert response.health.worst_case_margin <= response.health.expected_scenario_margin
    assert response.health.estimated_annual_exposure >= 0
    assert response.health.calculation_config.target_margin_percent == 45


def test_failure_modes_connect_clause_scenario_calculation_and_consequence():
    response = run_stress_test(terms(include_support_cap=True), assumptions(), 1_200_000, 240_000)
    mode = response.failure_modes[0]

    assert mode.affected_clause
    assert mode.scenario
    assert mode.formatted_financial_impact
    assert mode.recommended_remediation_category
    assert "Contract term:" in mode.explanation
    assert "deterministic calculation" in mode.explanation
    assert "consequence" in mode.explanation


def assumptions() -> CompanyAssumptions:
    return CompanyAssumptions(
        cost_per_api_call=0.2,
        monthly_infrastructure_cost=60_000,
        cost_per_support_hour=1_000,
        implementation_cost=200_000,
        minimum_acceptable_gross_margin=45,
        typical_support_consumption_hours=550,
        expected_annual_cost_inflation=0,
    )


def terms(include_support_cap: bool = False) -> list[EffectiveTerm]:
    base_terms = [
        term("currency", "INR", "iso_currency"),
        term("base_annual_price", "3000000", "currency_per_year"),
        term("included_usage", "1000000", "api_calls"),
        term("overage_pricing", "0.5", "INR_per_api_call"),
        term("recurring_discount", "10", "percent"),
        term("introductory_discount", "5", "percent"),
        term("service_credits", "2", "percent"),
        term("rebates", "1", "percent"),
        term("first_renewal_escalation", "0", "percent"),
        term("renewal_escalation", "8", "percent"),
    ]
    if include_support_cap:
        base_terms.extend(
            [
                term("support_allowance", "unlimited support", "text"),
                term("maximum_usage_payment_cap", "100000", "currency"),
            ]
        )
    return base_terms


def term(field_name: str, value: str, unit: str) -> EffectiveTerm:
    return EffectiveTerm(
        field_name=field_name,
        normalized_value=value,
        unit=unit,
        confidence=1,
        extraction_type=ExtractionType.explicit,
        review_status=ReviewStatus.confirmed,
        ambiguous=False,
    )
