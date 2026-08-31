from backend.app.models.economics import CompanyAssumptions
from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus
from backend.app.optimization.deal_optimizer import optimize_deal, prepare_revised_terms


def test_optimizer_returns_ranked_options_that_improve_health():
    response = optimize_deal(terms(), assumptions(), 1_200_000, 240_000, max_changed_clauses=2)

    assert response.options
    top = response.options[0]
    assert len(top.changed_terms) <= 2
    assert top.optimized_health.estimated_annual_exposure < top.current_health.estimated_annual_exposure
    assert top.reasons_for_recommendation
    assert top.customer_impact
    assert top.score >= response.options[-1].score
    assert top.trust_traces
    assert top.trust_traces[0].contract_evidence
    assert top.trust_traces[0].deterministic_calculation
    assert top.trust_traces[0].ai_reasoning_status in {
        "confirmed",
        "inferred",
        "requires_assumption",
        "requires_human_review",
        "assumption",
    }


def test_optimizer_can_add_structural_support_change_without_price_increase():
    response = optimize_deal(terms(include_unlimited_support=True), assumptions(), 1_200_000, 240_000, max_changed_clauses=1)

    fields = {change.field_name for option in response.options for change in option.changed_terms}
    assert "support_allowance" in fields
    assert any("No base price increase" in option.customer_impact for option in response.options)


def test_prepare_revised_terms_is_structured_and_requires_approval():
    response = optimize_deal(terms(include_unlimited_support=True), assumptions(), 1_200_000, 240_000, max_changed_clauses=2)
    artifact = prepare_revised_terms(response.options[0])

    assert artifact.subject_to_human_approval is True
    assert artifact.workflow_status == "Approved Recommendation"
    assert artifact.revised_terms
    assert artifact.revised_terms[0].current
    assert artifact.revised_terms[0].proposed
    assert "Healthy scenarios" in artifact.revised_terms[0].expected_effect
    assert "has not modified or signed" in artifact.approval_note


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


def terms(include_unlimited_support: bool = False) -> list[EffectiveTerm]:
    base_terms = [
        term("currency", "INR", "iso_currency"),
        term("base_annual_price", "3000000", "currency_per_year"),
        term("included_usage", "1000000", "api_calls"),
        term("overage_pricing", "0.5", "INR_per_api_call"),
        term("maximum_usage_payment_cap", "100000", "currency"),
        term("recurring_discount", "10", "percent"),
        term("introductory_discount", "5", "percent"),
        term("service_credits", "2", "percent"),
        term("rebates", "1", "percent"),
        term("renewal_escalation", "8", "percent"),
    ]
    if include_unlimited_support:
        base_terms.append(term("support_allowance", "unlimited support", "text"))
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
