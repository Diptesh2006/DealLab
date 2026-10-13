from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.models.api import ContractTextRequest
from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus
from backend.app.services.commercial_intelligence import SourceDocument, derive_effective_terms
from backend.app.services.contract_ingestion import extract_text_from_pdf, normalize_contract_text


def test_contract_request_and_effective_term_schema_are_validated():
    with pytest.raises(ValidationError):
        ContractTextRequest(text="too short")

    with pytest.raises(ValidationError):
        EffectiveTerm(
            field_name="currency",
            normalized_value="INR",
            unit="iso_currency",
            confidence=1.1,
            extraction_type=ExtractionType.explicit,
            review_status=ReviewStatus.confirmed,
            ambiguous=False,
        )


def test_acme_demo_pdfs_extract_effective_commercial_terms():
    demo_directory = Path("demo/acme-enterprise")
    documents = [
        SourceDocument(filename, document_type, precedence, normalize_contract_text(extract_text_from_pdf(demo_directory / filename)))
        for filename, document_type, precedence in [
            ("contract.pdf", "master_agreement", 0),
            ("amendment-1.pdf", "amendment", 1),
            ("approved-exception.pdf", "approved_exception", 2),
        ]
    ]
    term_map = {term.field_name: term for term in derive_effective_terms(documents)}

    assert term_map["base_annual_price"].normalized_value == "3000000"
    assert term_map["included_usage"].normalized_value == "12000000"
    assert term_map["maximum_usage_payment_cap"].normalized_value == "100000"
    assert term_map["maximum_usage_payment_cap"].unit == "INR_per_month"
    assert term_map["support_allowance"].normalized_value == "unlimited support"
    assert term_map["recurring_discount"].normalized_value == "0"
    assert term_map["first_renewal_escalation"].normalized_value == "0"
    assert term_map["renewal_escalation"].normalized_value == "8"
