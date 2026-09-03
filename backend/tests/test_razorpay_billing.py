from backend.app.models.intelligence import EffectiveTerm, ExtractionType, ReviewStatus
from backend.app.optimization.deal_optimizer import optimize_deal
from backend.app.services.razorpay_billing import build_billing_preview, create_test_billing_setup
from backend.tests.test_optimizer import assumptions, terms


def test_billing_preview_maps_only_fixed_recurring_terms():
    option = optimize_deal(terms(), assumptions(), 1_200_000, 240_000, max_changed_clauses=2).options[0]
    preview = build_billing_preview(terms(), option)

    assert preview.currency == "INR"
    assert preview.amount == 3_000_000
    assert preview.amount_subunits == 300_000_000
    assert preview.period == "yearly"
    assert preview.total_count == 1
    assert "overage pricing" in " ".join(preview.unsupported_terms)


def test_billing_preview_uses_approved_optimized_base_price_and_monthly_cycles():
    original_terms = [
        term("currency", "INR", "iso_currency"),
        term("base_annual_price", "1200000", "currency_per_year"),
        term("billing_frequency", "monthly", "frequency"),
        term("contract_duration", "24", "months"),
    ]
    option = optimize_deal(terms(), assumptions(), 1_200_000, 240_000, max_changed_clauses=1).options[0]
    changed_option = option.model_copy(
        update={
            "changed_terms": [
                option.changed_terms[0].model_copy(
                    update={"field_name": "base_annual_price", "proposed_value": "1500000"}
                )
            ]
        }
    )

    preview = build_billing_preview(original_terms, changed_option)

    assert preview.amount == 125000
    assert preview.period == "monthly"
    assert preview.total_count == 24


def test_billing_setup_fails_cleanly_when_test_credentials_are_not_configured(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    get_settings.cache_clear()

    with pytest.raises(HTTPException, match="credentials are unavailable") as error:
        create_test_billing_setup("ACME", "API agreement", sample_preview())

    assert error.value.status_code == 503
    get_settings.cache_clear()


def sample_preview():
    option = optimize_deal(terms(), assumptions(), 1_200_000, 240_000, max_changed_clauses=1).options[0]
    return build_billing_preview(terms(), option)


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
import pytest
from fastapi import HTTPException

from backend.app.core.config import get_settings
