from backend.app.models.economics import CompanyAssumptions, EconomicScenarioInput
from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus
from backend.app.simulation.economics import evaluate_financial_scenario, format_currency


def test_financial_scenario_formulas_are_deterministic():
    result = evaluate_financial_scenario(
        terms=[
            term("currency", "INR", "iso_currency"),
            term("base_annual_price", "3000000", "currency_per_year"),
            term("included_usage", "1000000", "api_calls"),
            term("overage_pricing", "0.5", "INR_per_api_call"),
            term("recurring_discount", "10", "percent"),
            term("introductory_discount", "5", "percent"),
            term("service_credits", "2", "percent"),
            term("rebates", "1", "percent"),
        ],
        assumptions=CompanyAssumptions(
            cost_per_api_call=0.2,
            monthly_infrastructure_cost=60000,
            cost_per_support_hour=1000,
            implementation_cost=200000,
            minimum_acceptable_gross_margin=45,
            typical_support_consumption_hours=550,
            expected_annual_cost_inflation=0,
        ),
        scenario=EconomicScenarioInput(
            name="Expected",
            expected_usage_units=1200000,
            usage_revenue=240000,
            apply_service_credits=True,
        ),
    )

    assert result.gross_revenue == 3340000
    assert result.effective_revenue_after_discounts == 2753830
    assert result.variable_costs == 960000
    assert result.support_costs == 550000
    assert result.total_cost == 1710000
    assert result.gross_profit == 1043830
    assert result.gross_margin_percent == 37.9
    assert result.downside_exposure == 195393.5
    assert result.difference_from_target_margin == -7.1


def test_renewal_pricing_handles_first_renewal_waiver():
    terms = [
        term("currency", "USD", "iso_currency"),
        term("base_annual_price", "100000", "currency_per_year"),
        term("first_renewal_escalation", "0", "percent"),
        term("renewal_escalation", "8", "percent"),
    ]
    assumptions = CompanyAssumptions(
        cost_per_api_call=0,
        monthly_infrastructure_cost=0,
        cost_per_support_hour=0,
        implementation_cost=0,
        minimum_acceptable_gross_margin=50,
        typical_support_consumption_hours=0,
        expected_annual_cost_inflation=0,
    )

    first = evaluate_financial_scenario(terms, assumptions, EconomicScenarioInput(name="First renewal", expected_usage_units=0, renewal_number=1))
    second = evaluate_financial_scenario(terms, assumptions, EconomicScenarioInput(name="Second renewal", expected_usage_units=0, renewal_number=2))

    assert first.gross_revenue == 100000
    assert second.gross_revenue == 108000


def test_currency_formatting_supports_indian_and_international_grouping():
    assert format_currency(3000000, "INR") == "₹30,00,000.00"
    assert format_currency(-300000, "INR") == "-₹3,00,000.00"
    assert format_currency(3000000, "USD") == "$3,000,000.00"


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
