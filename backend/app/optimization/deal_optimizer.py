from itertools import combinations

from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus
from backend.app.models.optimization import CandidateChange, OptimizationOption, OptimizeDealResponse
from backend.app.models.economics import CompanyAssumptions
from backend.app.simulation.economics import format_currency
from backend.app.simulation.stress import run_stress_test


OPTIMIZABLE_FIELDS = {
    "base_annual_price",
    "included_usage",
    "overage_pricing",
    "maximum_usage_payment_cap",
    "recurring_discount",
    "discount_duration",
    "support_allowance",
    "support_pricing",
    "renewal_escalation",
    "minimum_commitment",
    "service_credits",
    "sla_threshold",
}


def optimize_deal(
    terms: list[EffectiveTerm],
    assumptions: CompanyAssumptions,
    expected_usage_units: float,
    expected_usage_revenue: float,
    max_changed_clauses: int = 2,
) -> OptimizeDealResponse:
    current = run_stress_test(terms, assumptions, expected_usage_units, expected_usage_revenue)
    candidates = _bounded_candidates(terms, assumptions, current.health.critical_scenarios > 0)
    options: list[OptimizationOption] = []

    for size in range(1, max_changed_clauses + 1):
        for candidate_group in combinations(candidates, size):
            optimized_terms = _apply_changes(terms, list(candidate_group))
            optimized = run_stress_test(optimized_terms, assumptions, expected_usage_units, expected_usage_revenue)
            if not _improves(current.health, optimized.health):
                continue
            options.append(
                _option(
                    list(candidate_group),
                    current,
                    optimized,
                    terms,
                    optimized_terms,
                )
            )

    ranked = sorted(options, key=lambda option: option.score, reverse=True)
    return OptimizeDealResponse(current_health=current.health, options=_pareto(ranked)[:5])


def _bounded_candidates(
    terms: list[EffectiveTerm],
    assumptions: CompanyAssumptions,
    has_critical_scenarios: bool,
) -> list[CandidateChange]:
    term_map = {term.field_name: term for term in terms}
    candidates: list[CandidateChange] = []

    candidates.extend(_candidate(term_map, "maximum_usage_payment_cap", "unknown", "uncapped", "No base price increase", 2, "Remove cap so high adoption produces recoverable overage revenue."))
    candidates.extend(_support_allowance_candidate(term_map))
    candidates.extend(_candidate(term_map, "support_pricing", "unknown", str(round(assumptions.cost_per_support_hour * 1.5, 2)), "Charges only if support exceeds allowance", 2, "Recover incremental support load above included allowance."))
    candidates.extend(_discount_candidate(term_map, "recurring_discount", 0.75))
    candidates.extend(_discount_candidate(term_map, "service_credits", 0.5))
    candidates.extend(_price_candidate(term_map, has_critical_scenarios))
    candidates.extend(_numeric_candidate(term_map, "overage_pricing", 1.25, "Usage-based customer impact", 2, "Improve economics when adoption exceeds included usage."))
    candidates.extend(_numeric_candidate(term_map, "renewal_escalation", 1.5, "Future renewal impact only", 2, "Improve resilience against cost inflation after renewal."))

    return [candidate for candidate in candidates if candidate.field_name in OPTIMIZABLE_FIELDS]


def _candidate(
    term_map: dict[str, EffectiveTerm],
    field_name: str,
    replace_if_value: str,
    proposed: str,
    customer_impact: str,
    friction: int,
    rationale: str,
) -> list[CandidateChange]:
    term = term_map.get(field_name)
    original = term.normalized_value if term else "unknown"
    if original != replace_if_value and not (field_name == "maximum_usage_payment_cap" and original not in {"unknown", "uncapped", "0"}):
        return []
    return [
        CandidateChange(
            field_name=field_name,
            original_value=original,
            proposed_value=proposed,
            unit=term.unit if term else "text",
            customer_impact=customer_impact,
            commercial_friction=friction,
            rationale=rationale,
        )
    ]


def _numeric_candidate(
    term_map: dict[str, EffectiveTerm],
    field_name: str,
    multiplier: float,
    customer_impact: str,
    friction: int,
    rationale: str,
) -> list[CandidateChange]:
    term = term_map.get(field_name)
    if not term:
        return []
    value = _num(term.normalized_value)
    if value <= 0:
        return []
    proposed = round(value * multiplier, 2)
    if proposed == value:
        return []
    return [
        CandidateChange(
            field_name=field_name,
            original_value=term.normalized_value,
            proposed_value=str(proposed),
            unit=term.unit,
            customer_impact=customer_impact,
            commercial_friction=friction,
            rationale=rationale,
        )
    ]


def _support_allowance_candidate(term_map: dict[str, EffectiveTerm]) -> list[CandidateChange]:
    term = term_map.get("support_allowance")
    original = term.normalized_value if term else "unknown"
    if original != "unknown" and "unlimited" not in original.lower():
        return []
    return [
        CandidateChange(
            field_name="support_allowance",
            original_value=original,
            proposed_value="30 hours/month included; excess billed at support pricing",
            unit=term.unit if term else "text",
            customer_impact="No base price increase",
            commercial_friction=3,
            rationale="Bound support exposure while preserving included customer support.",
        )
    ]


def _discount_candidate(term_map: dict[str, EffectiveTerm], field_name: str, multiplier: float) -> list[CandidateChange]:
    term = term_map.get(field_name)
    if not term:
        return []
    value = _num(term.normalized_value)
    if value <= 0:
        return []
    proposed = round(value * multiplier, 2)
    return [
        CandidateChange(
            field_name=field_name,
            original_value=term.normalized_value,
            proposed_value=str(proposed),
            unit=term.unit,
            customer_impact="Reduces concession value",
            commercial_friction=3,
            rationale="Reduce concession leakage while keeping negotiated structure intact.",
        )
    ]


def _price_candidate(term_map: dict[str, EffectiveTerm], has_critical_scenarios: bool) -> list[CandidateChange]:
    multiplier = 1.08 if has_critical_scenarios else 1.04
    return _numeric_candidate(
        term_map,
        "base_annual_price",
        multiplier,
        f"{round((multiplier - 1) * 100, 1)}% base price increase",
        5,
        "Use only when lower-friction structural changes do not restore enough resilience.",
    )


def _apply_changes(terms: list[EffectiveTerm], changes: list[CandidateChange]) -> list[EffectiveTerm]:
    change_map = {change.field_name: change for change in changes}
    optimized: list[EffectiveTerm] = []
    present_fields = set()

    for term in terms:
        present_fields.add(term.field_name)
        change = change_map.get(term.field_name)
        if change:
            optimized.append(
                term.model_copy(
                    update={
                        "normalized_value": change.proposed_value,
                        "unit": change.unit,
                        "extraction_type": ExtractionType.inferred,
                        "review_status": ReviewStatus.requires_human_review,
                        "ambiguous": False,
                    }
                )
            )
        else:
            optimized.append(term)

    for change in changes:
        if change.field_name not in present_fields:
            optimized.append(
                EffectiveTerm(
                    field_name=change.field_name,
                    normalized_value=change.proposed_value,
                    unit=change.unit,
                    confidence=0.82,
                    extraction_type=ExtractionType.inferred,
                    review_status=ReviewStatus.requires_human_review,
                    ambiguous=False,
                )
            )
    return optimized


def _option(
    changes: list[CandidateChange],
    current,
    optimized,
    original_terms: list[EffectiveTerm],
    optimized_terms: list[EffectiveTerm],
) -> OptimizationOption:
    currency = optimized.scenarios[0].economics.currency if optimized.scenarios else "USD"
    current_status = {item.scenario.name: item.status for item in current.scenarios}
    scenarios_fixed = [
        item.scenario.name
        for item in optimized.scenarios
        if current_status.get(item.scenario.name) != "pass" and item.status == "pass"
    ]
    still_risky = [item.scenario.name for item in optimized.scenarios if item.status != "pass"]
    improvement = current.health.estimated_annual_exposure - optimized.health.estimated_annual_exposure
    score = _score(current.health, optimized.health, changes)
    title = " + ".join(_title_for(change) for change in changes)

    return OptimizationOption(
        title=title,
        changed_terms=changes,
        current_health=current.health,
        optimized_health=optimized.health,
        financial_improvement=round(improvement, 2),
        formatted_financial_improvement=format_currency(improvement, currency),
        formatted_current_annual_exposure=format_currency(current.health.estimated_annual_exposure, currency),
        formatted_optimized_annual_exposure=format_currency(optimized.health.estimated_annual_exposure, currency),
        scenarios_fixed=scenarios_fixed,
        scenarios_still_risky=still_risky,
        customer_impact=_customer_impact(changes, original_terms, optimized_terms),
        reasons_for_recommendation=_reasons(current.health, optimized.health, changes, scenarios_fixed),
        score=round(score, 4),
    )


def _score(current_health, optimized_health, changes: list[CandidateChange]) -> float:
    pass_gain = optimized_health.percentage_above_target_margin - current_health.percentage_above_target_margin
    expected_gain = optimized_health.expected_scenario_margin - current_health.expected_scenario_margin
    downside_gain = optimized_health.downside_margin - current_health.downside_margin
    exposure_gain = max(0, current_health.estimated_annual_exposure - optimized_health.estimated_annual_exposure) / 100000
    friction_penalty = sum(change.commercial_friction for change in changes) * 2
    clause_penalty = len(changes) * 4
    price_penalty = _base_price_increase_percent(changes) * 1.2
    return pass_gain * 1.4 + expected_gain * 1.2 + downside_gain * 1.5 + exposure_gain - friction_penalty - clause_penalty - price_penalty


def _pareto(options: list[OptimizationOption]) -> list[OptimizationOption]:
    pareto: list[OptimizationOption] = []
    seen_changes: set[tuple[str, ...]] = set()
    for option in options:
        key = tuple(sorted(change.field_name for change in option.changed_terms))
        if key in seen_changes:
            continue
        seen_changes.add(key)
        if option.financial_improvement > 0:
            pareto.append(option)
    return pareto


def _improves(current_health, optimized_health) -> bool:
    return (
        optimized_health.percentage_above_target_margin > current_health.percentage_above_target_margin
        or optimized_health.downside_margin > current_health.downside_margin
        or optimized_health.estimated_annual_exposure < current_health.estimated_annual_exposure
    )


def _customer_impact(changes: list[CandidateChange], original_terms: list[EffectiveTerm], optimized_terms: list[EffectiveTerm]) -> str:
    price_change = _base_price_increase_percent(changes)
    if price_change > 0:
        return f"{round(price_change, 2)}% base price increase plus {len(changes) - 1} structural change(s)."
    return f"No base price increase; {len(changes)} structural clause change(s)."


def _reasons(current_health, optimized_health, changes: list[CandidateChange], scenarios_fixed: list[str]) -> list[str]:
    reasons = [
        f"Healthy scenarios improve from {current_health.percentage_above_target_margin}% to {optimized_health.percentage_above_target_margin}%.",
        f"Downside margin improves from {current_health.downside_margin}% to {optimized_health.downside_margin}%.",
    ]
    if scenarios_fixed:
        reasons.append(f"Fixes {len(scenarios_fixed)} scenario(s): {', '.join(scenarios_fixed)}.")
    reasons.append(f"Touches only {len(changes)} clause(s): {', '.join(change.field_name for change in changes)}.")
    return reasons


def _title_for(change: CandidateChange) -> str:
    labels = {
        "maximum_usage_payment_cap": "Remove overage cap",
        "support_allowance": "Cap included support",
        "support_pricing": "Price excess support",
        "recurring_discount": "Reduce recurring discount",
        "service_credits": "Reduce service credits",
        "base_annual_price": "Adjust base price",
        "overage_pricing": "Increase overage price",
        "renewal_escalation": "Increase renewal uplift",
    }
    return labels.get(change.field_name, change.field_name.replace("_", " ").title())


def _base_price_increase_percent(changes: list[CandidateChange]) -> float:
    for change in changes:
        if change.field_name == "base_annual_price":
            original = _num(change.original_value)
            proposed = _num(change.proposed_value)
            return ((proposed - original) / original * 100) if original else 0
    return 0


def _num(value: str) -> float:
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0
