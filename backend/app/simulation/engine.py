from backend.app.models.deal import CommercialTerms, Scenario, ScenarioResult


TARGET_MARGIN_PERCENT = 55.0


def evaluate_scenario(terms: CommercialTerms, scenario: Scenario) -> ScenarioResult:
    annual_revenue = terms.annual_contract_value * (1 - terms.discount_percent / 100)
    scenario_revenue = annual_revenue * scenario.revenue_multiplier
    variable_cost = scenario_revenue * (terms.variable_cost_percent / 100) * scenario.cost_multiplier
    support_cost = terms.support_cost * scenario.support_cost_multiplier
    total_cost = variable_cost + support_cost
    gross_margin = scenario_revenue - total_cost
    gross_margin_percent = (gross_margin / scenario_revenue * 100) if scenario_revenue else 0
    target_profit = scenario_revenue * (TARGET_MARGIN_PERCENT / 100)
    downside_exposure = max(0, target_profit - gross_margin)

    return ScenarioResult(
        scenario_name=scenario.name,
        revenue=round(scenario_revenue, 2),
        cost=round(total_cost, 2),
        gross_margin=round(gross_margin, 2),
        gross_margin_percent=round(gross_margin_percent, 2),
        downside_exposure=round(downside_exposure, 2),
    )


def evaluate_deal(terms: CommercialTerms, scenarios: list[Scenario]) -> list[ScenarioResult]:
    return [evaluate_scenario(terms, scenario) for scenario in scenarios]
