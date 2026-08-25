import re

from backend.app.models.deal import CommercialTerms


def _money(pattern: str, text: str, default: float) -> float:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return default
    return float(match.group(1).replace(",", ""))


def _percent(pattern: str, text: str, default: float) -> float:
    match = re.search(pattern, text, re.IGNORECASE)
    return float(match.group(1)) if match else default


def _integer(pattern: str, text: str, default: int) -> int:
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1)) if match else default


def extract_commercial_terms(text: str) -> CommercialTerms:
    """Deterministic MVP extractor; replace/enrich with LLM extraction evidence later."""
    customer_match = re.search(r"(?:customer|client)\s*:\s*([A-Za-z0-9 .,&-]+)", text, re.IGNORECASE)
    customer_name = customer_match.group(1).strip() if customer_match else None

    return CommercialTerms(
        customer_name=customer_name,
        annual_contract_value=_money(r"(?:ACV|annual contract value)\D+\$?([0-9,]+(?:\.\d+)?)", text, 250000),
        term_months=_integer(r"(?:term|contract term)\D+([0-9]+)\s*(?:months|month)", text, 24),
        discount_percent=_percent(r"(?:discount)\D+([0-9]+(?:\.\d+)?)\s*%", text, 15),
        usage_commitment=_money(r"(?:usage commitment|minimum commitment)\D+\$?([0-9,]+(?:\.\d+)?)", text, 0),
        variable_cost_percent=_percent(r"(?:variable cost|cost of delivery)\D+([0-9]+(?:\.\d+)?)\s*%", text, 38),
        support_cost=_money(r"(?:support cost|implementation support)\D+\$?([0-9,]+(?:\.\d+)?)", text, 30000),
        payment_terms_days=_integer(r"(?:net|payment terms)\D*([0-9]+)", text, 60),
        auto_renewal=bool(re.search(r"auto(?:matic)? renewal|auto-renew", text, re.IGNORECASE)),
        liability_cap_multiplier=_percent(r"(?:liability cap)\D+([0-9]+(?:\.\d+)?)\s*x", text, 1.0),
    )
