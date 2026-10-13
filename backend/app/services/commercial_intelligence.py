from dataclasses import dataclass
import re

from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus


EXPECTED_FIELDS = [
    "base_annual_price",
    "billing_frequency",
    "contract_duration",
    "currency",
    "included_usage",
    "usage_unit",
    "overage_pricing",
    "minimum_commitment",
    "maximum_usage_payment_cap",
    "introductory_discount",
    "discount_duration",
    "recurring_discount",
    "renewal_date",
    "first_renewal_escalation",
    "renewal_escalation",
    "support_allowance",
    "support_pricing",
    "implementation_obligations",
    "service_credits",
    "sla_threshold",
    "penalty_clauses",
    "rebates",
    "cancellation_fees",
    "early_termination_clauses",
    "unusual_custom_commercial_clauses",
]


@dataclass(frozen=True)
class SourceDocument:
    filename: str
    document_type: str
    precedence_order: int
    text: str


def derive_effective_terms(documents: list[SourceDocument]) -> list[EffectiveTerm]:
    terms_by_field: dict[str, EffectiveTerm] = {}
    for document in sorted(documents, key=lambda item: item.precedence_order):
        for term in _extract_terms_from_document(document):
            if term.field_name == "currency" and term.field_name in terms_by_field:
                continue
            terms_by_field[term.field_name] = term

    _apply_effective_agreement_reasoning(documents, terms_by_field)

    for field_name in EXPECTED_FIELDS:
        terms_by_field.setdefault(field_name, _unknown_term(field_name))

    return [terms_by_field[field_name] for field_name in EXPECTED_FIELDS]


def _extract_terms_from_document(document: SourceDocument) -> list[EffectiveTerm]:
    text = document.text
    terms: list[EffectiveTerm] = []

    patterns = [
        ("base_annual_price", r"(?:ACV|annual contract value|annual base price|base annual price)\D+(\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)", "currency_per_year"),
        ("contract_duration", r"(?:term|contract duration|contract term)\D+([0-9]+)\s*(months|month|years|year)", "duration"),
        ("included_usage", r"(?:included usage|included volume)\D+([0-9,]+(?:\.\d+)?)\s*([A-Za-z ]+)", "usage"),
        ("overage_pricing", r"(?:overage|overage pricing)\D+(\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)\s*(?:per|/)\s*([A-Za-z ]+)", "currency_per_unit"),
        ("minimum_commitment", r"(?:minimum commitment|usage commitment)\D+(\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)", "currency"),
        ("maximum_usage_payment_cap", r"(?:maximum usage|payment cap|usage cap|overage charges? (?:are )?capped)\D+(\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)", "currency"),
        ("introductory_discount", r"(?:introductory discount|initial discount)\D+([0-9]+(?:\.\d+)?)\s*%", "percent"),
        ("discount_duration", r"(?:discount duration|introductory period|introductory discount[^.]{0,80}?first)\D*([0-9]+)\s*(months|month|years|year)", "duration"),
        ("recurring_discount", r"(?:recurring discount|ongoing discount)\D+([0-9]+(?:\.\d+)?)\s*%", "percent"),
        ("renewal_date", r"(?:renewal date|renews on)\D+([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", "date"),
        ("renewal_escalation", r"(?:annual increase|renewal uplift|renewal escalation|price increase)\D+([0-9]+(?:\.\d+)?)\s*%", "percent"),
        ("support_allowance", r"(?:support allowance)\D+([0-9,]+(?:\.\d+)?)\s*([A-Za-z ]+)", "allowance"),
        ("support_pricing", r"(?:support pricing|support cost)\D+(\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)", "currency"),
        ("service_credits", r"(?:service credits?)\D+([0-9]+(?:\.\d+)?)\s*%", "percent"),
        ("sla_threshold", r"(?:SLA|service level)\D+([0-9]+(?:\.\d+)?)\s*%", "percent"),
        ("rebates", r"(?:rebate)\D+([0-9]+(?:\.\d+)?)\s*%", "percent"),
        ("cancellation_fees", r"(?:cancellation fee)\D+(\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)", "currency"),
    ]

    for field_name, pattern, unit in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            terms.append(_term_from_match(field_name, match, unit, document))

    annual_usage = re.search(
        r"includes\s+[0-9,]+(?:\.\d+)?\s+API units per month,\s+equivalent to\s+([0-9,]+(?:\.\d+)?)\s+API units per\s+(?:contract )?year",
        text,
        re.IGNORECASE,
    )
    if annual_usage:
        terms.append(
            _explicit_text_value(
                "included_usage",
                annual_usage.group(1).replace(",", ""),
                "api_units_per_year",
                annual_usage,
                document,
                confidence=0.97,
            )
        )

    monthly_overage_cap = re.search(
        r"monthly overage charges are capped at\s+(?:\$|USD|INR|EUR|GBP)?\s*([0-9,]+(?:\.\d+)?)\s+per month",
        text,
        re.IGNORECASE,
    )
    if monthly_overage_cap:
        terms.append(
            _explicit_text_value(
                "maximum_usage_payment_cap",
                monthly_overage_cap.group(1).replace(",", ""),
                f"{_detect_currency(text) or 'currency'}_per_month",
                monthly_overage_cap,
                document,
                confidence=0.96,
            )
        )

    unlimited_support = re.search(r"(?:support allowance[^.]{0,160}?unlimited\s+support|interpreted as unlimited\s+support)", text, re.IGNORECASE)
    if unlimited_support:
        terms.append(
            _explicit_text_value("support_allowance", "unlimited support", "text", unlimited_support, document, confidence=0.82)
        )
    no_support_fee = re.search(r"no separate support (?:overage )?fee is specified", text, re.IGNORECASE)
    if no_support_fee:
        terms.append(_explicit_text_value("support_pricing", "0", "currency_per_hour", no_support_fee, document, confidence=0.86))
    no_rebate = re.search(r"no recurring rebate applies", text, re.IGNORECASE)
    if no_rebate:
        terms.append(_explicit_text_value("rebates", "0", "percent", no_rebate, document, confidence=0.95))
    no_recurring_discount = re.search(r"discount does not apply after month\s+[0-9]+", text, re.IGNORECASE)
    if no_recurring_discount:
        terms.append(_explicit_text_value("recurring_discount", "0", "percent", no_recurring_discount, document, confidence=0.9))

    boolean_clauses = [
        ("billing_frequency", r"(?:\b(monthly|annual|annually|quarterly)\s+billing\b|billing frequency is\s+(monthly|annual|annually|quarterly))", "frequency"),
        ("implementation_obligations", r"(implementation obligations?.{0,180})", "text"),
        ("penalty_clauses", r"(penalt(?:y|ies).{0,180})", "text"),
        ("early_termination_clauses", r"(early termination.{0,180})", "text"),
        ("unusual_custom_commercial_clauses", r"((?:custom clause|custom commercial|non-standard|unusual).{0,180})", "text"),
    ]
    for field_name, pattern, unit in boolean_clauses:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            terms.append(_text_term(field_name, match, unit, document))

    currency = _detect_currency(text)
    if currency:
        terms.append(
            EffectiveTerm(
                field_name="currency",
                normalized_value=currency,
                unit="iso_currency",
                source_document=document.filename,
                source_page=1,
                evidence_excerpt=currency,
                confidence=0.88,
                extraction_type=ExtractionType.explicit,
                review_status=ReviewStatus.confirmed,
                ambiguous=False,
            )
        )

    return terms


def _apply_effective_agreement_reasoning(documents: list[SourceDocument], terms_by_field: dict[str, EffectiveTerm]) -> None:
    combined = "\n".join(document.text for document in sorted(documents, key=lambda item: item.precedence_order))
    waiver = re.search(r"first renewal (?:increase|uplift|escalation) (?:is )?waived|waive[sd]? .*first renewal", combined, re.IGNORECASE)
    escalation = terms_by_field.get("renewal_escalation")
    if waiver and escalation:
        terms_by_field["first_renewal_escalation"] = EffectiveTerm(
            field_name="first_renewal_escalation",
            normalized_value="0",
            unit="percent",
            effective_from="first_renewal",
            source_document=_waiver_source(documents),
            source_page=1,
            evidence_excerpt=_excerpt(combined, waiver.start(), waiver.end()),
            confidence=0.9,
            extraction_type=ExtractionType.inferred,
            review_status=ReviewStatus.inferred,
            ambiguous=False,
        )
        terms_by_field["renewal_escalation"] = escalation.model_copy(update={"effective_from": "second_renewal"})


def _term_from_match(field_name: str, match: re.Match[str], unit: str, document: SourceDocument) -> EffectiveTerm:
    groups = [group for group in match.groups() if group]
    normalized_value = _first_numeric(groups)
    normalized_unit = unit
    if field_name == "contract_duration" and len(groups) >= 2:
        normalized_unit = groups[1].lower()
    if field_name == "included_usage" and len(groups) >= 2:
        normalized_unit = _clean_unit(groups[1])
    if field_name == "overage_pricing" and len(groups) >= 2:
        normalized_unit = f"{_detect_currency(document.text) or 'currency'}_per_{_clean_unit(groups[-1])}"
    return EffectiveTerm(
        field_name=field_name,
        normalized_value=normalized_value,
        unit=normalized_unit,
        source_document=document.filename,
        source_page=1,
        evidence_excerpt=_excerpt(document.text, match.start(), match.end()),
        confidence=0.86,
        extraction_type=ExtractionType.explicit,
        review_status=ReviewStatus.confirmed,
        ambiguous=False,
    )


def _text_term(field_name: str, match: re.Match[str], unit: str, document: SourceDocument) -> EffectiveTerm:
    value = next((group for group in match.groups() if group), match.group(0))
    return EffectiveTerm(
        field_name=field_name,
        normalized_value=value.strip(),
        unit=unit,
        source_document=document.filename,
        source_page=1,
        evidence_excerpt=_excerpt(document.text, match.start(), match.end()),
        confidence=0.76,
        extraction_type=ExtractionType.explicit,
        review_status=ReviewStatus.requires_human_review,
        ambiguous=True,
    )


def _explicit_text_value(
    field_name: str,
    value: str,
    unit: str,
    match: re.Match[str],
    document: SourceDocument,
    confidence: float,
) -> EffectiveTerm:
    return EffectiveTerm(
        field_name=field_name,
        normalized_value=value,
        unit=unit,
        source_document=document.filename,
        source_page=1,
        evidence_excerpt=_excerpt(document.text, match.start(), match.end()),
        confidence=confidence,
        extraction_type=ExtractionType.explicit,
        review_status=ReviewStatus.confirmed,
        ambiguous=False,
    )


def _unknown_term(field_name: str) -> EffectiveTerm:
    return EffectiveTerm(
        field_name=field_name,
        normalized_value="unknown",
        unit="unknown",
        confidence=0,
        extraction_type=ExtractionType.unknown,
        review_status=ReviewStatus.requires_human_review,
        ambiguous=True,
    )


def _detect_currency(text: str) -> str | None:
    if re.search(r"\bUSD\b|\$", text, re.IGNORECASE):
        return "USD"
    if re.search(r"\bINR\b|₹", text, re.IGNORECASE):
        return "INR"
    if re.search(r"\bEUR\b|€", text, re.IGNORECASE):
        return "EUR"
    if re.search(r"\bGBP\b|£", text, re.IGNORECASE):
        return "GBP"
    return None


def _first_numeric(groups: list[str]) -> str:
    for group in groups:
        if re.search(r"[0-9]", group):
            return group.replace(",", "")
    return groups[-1].strip() if groups else "unknown"


def _normalize_currency(value: str) -> str:
    if value == "$":
        return "USD"
    return value.upper()


def _clean_unit(value: str) -> str:
    return re.split(r"[.;,\n]", value.strip().lower(), maxsplit=1)[0].strip()


def _waiver_source(documents: list[SourceDocument]) -> str | None:
    for document in sorted(documents, key=lambda item: item.precedence_order, reverse=True):
        if re.search(r"first renewal (?:increase|uplift|escalation) (?:is )?waived|waive[sd]? .*first renewal", document.text, re.IGNORECASE):
            return document.filename
    return None


def _excerpt(text: str, start: int, end: int) -> str:
    excerpt_start = max(0, start - 50)
    excerpt_end = min(len(text), end + 80)
    return " ".join(text[excerpt_start:excerpt_end].split())
