from backend.app.models.economics import (
    CompanyAssumptions,
    EconomicScenarioInput,
    FinancialLineItem,
    ScenarioEconomicsResult,
    TraceReference,
)
from backend.app.models.intelligence import EffectiveTerm


def evaluate_financial_scenario(
    terms: list[EffectiveTerm],
    assumptions: CompanyAssumptions,
    scenario: EconomicScenarioInput,
) -> ScenarioEconomicsResult:
    term_map = {term.field_name: term for term in terms}
    currency = _term_value(term_map, "currency", "USD")
    base_revenue = _number_term(term_map, "base_annual_price")
    included_usage = _number_term(term_map, "included_usage")
    overage_price = _number_term(term_map, "overage_pricing")
    recurring_discount_percent = _number_term(term_map, "recurring_discount")
    temporary_discount_percent = _number_term(term_map, "introductory_discount") if scenario.apply_temporary_discount else 0
    overage_revenue_cap = _annualized_cap(term_map, "maximum_usage_payment_cap")
    service_credit_percent = _number_term(term_map, "service_credits") if scenario.apply_service_credits else 0
    rebate_percent = _number_term(term_map, "rebates") if scenario.apply_rebates else 0
    renewal_uplift_percent = _renewal_uplift(term_map, scenario.renewal_number)
    support_hours = scenario.support_hours if scenario.support_hours is not None else assumptions.typical_support_consumption_hours

    renewal_revenue = base_revenue * (renewal_uplift_percent / 100)
    billable_overage_units = max(0, scenario.expected_usage_units - included_usage)
    uncapped_overage_revenue = billable_overage_units * overage_price
    overage_revenue = min(uncapped_overage_revenue, overage_revenue_cap) if overage_revenue_cap else uncapped_overage_revenue
    cap_adjustment = max(0, uncapped_overage_revenue - overage_revenue)
    gross_revenue = base_revenue + renewal_revenue + scenario.usage_revenue + overage_revenue

    recurring_discount = gross_revenue * (recurring_discount_percent / 100)
    temporary_discount = gross_revenue * (temporary_discount_percent / 100)
    discounted_revenue = gross_revenue - recurring_discount - temporary_discount
    rebates = discounted_revenue * (rebate_percent / 100)
    credits_penalties = discounted_revenue * (service_credit_percent / 100)
    effective_revenue = discounted_revenue - rebates - credits_penalties

    inflation_multiplier = 1 + assumptions.expected_annual_cost_inflation / 100
    variable_costs = scenario.expected_usage_units * assumptions.cost_per_api_call * scenario.cost_multiplier
    infrastructure_cost = assumptions.monthly_infrastructure_cost * 12 * inflation_multiplier * scenario.cost_multiplier
    support_costs = support_hours * assumptions.cost_per_support_hour * inflation_multiplier * scenario.cost_multiplier
    implementation_cost = assumptions.implementation_cost
    total_cost = variable_costs + infrastructure_cost + support_costs + implementation_cost
    gross_profit = effective_revenue - total_cost
    gross_margin_percent = (gross_profit / effective_revenue * 100) if effective_revenue else 0
    target_profit = effective_revenue * (assumptions.minimum_acceptable_gross_margin / 100)
    downside_exposure = max(0, target_profit - gross_profit)
    difference_from_target_margin = gross_margin_percent - assumptions.minimum_acceptable_gross_margin
    arr = effective_revenue
    expected_customer_contribution = gross_profit

    breakdown = [
        _line("Base contract revenue", base_revenue, currency, "base_annual_price", None, None),
        _line("Renewal pricing", renewal_revenue, currency, "renewal_escalation", None, "renewal_number"),
        _line("Usage revenue", scenario.usage_revenue, currency, None, None, "usage_revenue"),
        _line("Overage revenue", overage_revenue, currency, "overage_pricing / maximum_usage_payment_cap", None, "expected_usage_units"),
        _line("Recurring discount", -recurring_discount, currency, "recurring_discount", None, None),
        _line("Temporary discount", -temporary_discount, currency, "introductory_discount", None, "apply_temporary_discount"),
        _line("Revenue cap adjustment", -cap_adjustment, currency, "maximum_usage_payment_cap", None, None),
        _line("Rebates", -rebates, currency, "rebates", None, "apply_rebates"),
        _line("Credits and penalties", -credits_penalties, currency, "service_credits", None, "apply_service_credits"),
        _line("Infrastructure cost", -infrastructure_cost, currency, None, "monthly_infrastructure_cost", None),
        _line("Variable API cost", -variable_costs, currency, None, "cost_per_api_call", "expected_usage_units"),
        _line("Support cost", -support_costs, currency, None, "cost_per_support_hour", "support_hours"),
        _line("Implementation cost", -implementation_cost, currency, "implementation_obligations", "implementation_cost", None),
        _line("Gross profit", gross_profit, currency, None, None, None),
    ]

    return ScenarioEconomicsResult(
        scenario_name=scenario.name,
        currency=currency,
        gross_revenue=round(gross_revenue, 2),
        effective_revenue_after_discounts=round(effective_revenue, 2),
        variable_costs=round(variable_costs + infrastructure_cost, 2),
        support_costs=round(support_costs, 2),
        credits_penalties=round(credits_penalties, 2),
        total_cost=round(total_cost, 2),
        gross_profit=round(gross_profit, 2),
        gross_margin_percent=round(gross_margin_percent, 2),
        arr=round(arr, 2),
        expected_customer_contribution=round(expected_customer_contribution, 2),
        downside_exposure=round(downside_exposure, 2),
        difference_from_target_margin=round(difference_from_target_margin, 2),
        breakdown=breakdown,
    )


def format_currency(amount: float, currency: str) -> str:
    sign = "-" if amount < 0 else ""
    absolute = abs(round(amount, 2))
    whole, _, cents = f"{absolute:.2f}".partition(".")
    symbol = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£"}.get(currency, f"{currency} ")
    grouped = _group_indian(whole) if currency == "INR" else _group_international(whole)
    return f"{sign}{symbol}{grouped}.{cents}"


def _line(
    label: str,
    amount: float,
    currency: str,
    contract_term: str | None,
    company_assumption: str | None,
    scenario_input: str | None,
) -> FinancialLineItem:
    return FinancialLineItem(
        label=label,
        amount=round(amount, 2),
        formatted_amount=format_currency(amount, currency),
        trace=TraceReference(
            contract_term=contract_term,
            company_assumption=company_assumption,
            scenario_input=scenario_input,
        ),
    )


def _number_term(term_map: dict[str, EffectiveTerm], field_name: str) -> float:
    value = _term_value(term_map, field_name, "0")
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0


def _term_value(term_map: dict[str, EffectiveTerm], field_name: str, default: str) -> str:
    term = term_map.get(field_name)
    if term is None or term.normalized_value in {"unknown", "requires_assumption", "requires_human_review"}:
        return default
    return term.normalized_value


def _term_unit(term_map: dict[str, EffectiveTerm], field_name: str) -> str:
    term = term_map.get(field_name)
    return term.unit if term else ""


def _annualized_cap(term_map: dict[str, EffectiveTerm], field_name: str) -> float:
    cap = _number_term(term_map, field_name)
    unit = _term_unit(term_map, field_name).lower()
    if cap > 0 and "month" in unit:
        return cap * 12
    return cap


def _renewal_uplift(term_map: dict[str, EffectiveTerm], renewal_number: int) -> float:
    if renewal_number == 1 and "first_renewal_escalation" in term_map:
        return _number_term(term_map, "first_renewal_escalation")
    if renewal_number >= 1:
        return _number_term(term_map, "renewal_escalation")
    return 0


def _group_international(whole: str) -> str:
    parts: list[str] = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    return ",".join(reversed(parts))


def _group_indian(whole: str) -> str:
    if len(whole) <= 3:
        return whole
    last_three = whole[-3:]
    rest = whole[:-3]
    groups: list[str] = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    return ",".join(reversed(groups)) + "," + last_three
