from backend.app.models.deal import CommercialTerms, ScenarioResult


def identify_fragile_terms(terms: CommercialTerms, results: list[ScenarioResult]) -> list[str]:
    fragile_terms: list[str] = []
    worst_margin = min(result.gross_margin_percent for result in results)

    if worst_margin < 45:
        fragile_terms.append("Gross margin falls below the 45% downside guardrail.")
    if terms.discount_percent > 25:
        fragile_terms.append("Discount depth materially reduces available downside cushion.")
    if terms.payment_terms_days > 60:
        fragile_terms.append("Payment terms extend beyond standard working-capital tolerance.")
    if terms.usage_commitment == 0:
        fragile_terms.append("No usage commitment leaves revenue exposed to adoption risk.")
    if terms.liability_cap_multiplier > 1:
        fragile_terms.append("Liability cap exceeds one year of contract value.")

    return fragile_terms


def recommend_changes(terms: CommercialTerms, results: list[ScenarioResult]) -> list[str]:
    recommendations: list[str] = []
    worst_margin = min(result.gross_margin_percent for result in results)

    if worst_margin < 45:
        recommendations.append("Reduce discount or add a ramped minimum commitment until downside margin is at least 45%.")
    if terms.payment_terms_days > 60:
        recommendations.append("Move payment terms to Net 45 or add upfront invoicing for implementation support.")
    if terms.usage_commitment == 0:
        recommendations.append("Add a minimum annual usage commitment tied to reserved capacity.")
    if terms.liability_cap_multiplier > 1:
        recommendations.append("Cap liability at fees paid in the previous 12 months, with narrow negotiated exceptions.")

    return recommendations or ["Deal is within current MVP guardrails; keep human approval before signature."]


def health_score(results: list[ScenarioResult], fragile_terms: list[str]) -> int:
    worst_margin = min(result.gross_margin_percent for result in results)
    exposure_penalty = min(35, int(sum(result.downside_exposure for result in results) / 10000))
    margin_penalty = max(0, int((55 - worst_margin) * 1.5))
    fragility_penalty = len(fragile_terms) * 8
    return max(0, min(100, 100 - exposure_penalty - margin_penalty - fragility_penalty))
