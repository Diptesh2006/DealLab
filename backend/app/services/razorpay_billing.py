import base64
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from backend.app.core.config import get_settings
from backend.app.models.billing import RazorpayBillingPreview
from backend.app.models.intelligence import EffectiveTerm
from backend.app.models.optimization import OptimizationOption


RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def build_billing_preview(terms: list[EffectiveTerm], option: OptimizationOption) -> RazorpayBillingPreview:
    values = {term.field_name: term.normalized_value for term in terms}
    values.update({change.field_name: change.proposed_value for change in option.changed_terms})
    currency = values.get("currency", "INR").upper()
    if currency not in {"INR", "USD", "EUR", "GBP"}:
        raise HTTPException(status_code=422, detail=f"Razorpay billing preview does not support currency '{currency}'.")

    amount = _number(values.get("base_annual_price", "0"))
    if amount <= 0:
        raise HTTPException(status_code=422, detail="A confirmed positive base annual price is required for Razorpay billing setup.")

    frequency = values.get("billing_frequency", "annual").lower()
    period = "monthly" if "month" in frequency else "yearly"
    cycle_amount = amount / 12 if period == "monthly" else amount
    duration_months = max(12, int(_number(values.get("contract_duration", values.get("minimum_commitment", "12")))))
    total_count = max(1, duration_months if period == "monthly" else (duration_months + 11) // 12)

    return RazorpayBillingPreview(
        currency=currency,
        amount=round(cycle_amount),
        amount_subunits=round(cycle_amount * 100),
        period=period,
        total_count=total_count,
        mapped_terms=["base_annual_price", "billing_frequency", "contract_duration"],
        unsupported_terms=[
            "included_usage and overage pricing",
            "usage/payment caps",
            "temporary or recurring discounts",
            "support allowance and support pricing",
            "renewal uplift",
            "service credits, SLA thresholds, rebates, and legal clauses",
        ],
        note=(
            "Razorpay receives only the fixed recurring base charge. Commercial usage, discount, support, "
            "renewal, and legal mechanics remain governed by approved contract and billing operations."
        ),
    )


def create_test_billing_setup(customer_name: str, deal_name: str, preview: RazorpayBillingPreview) -> dict[str, str]:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay test credentials are unavailable. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET on the backend to prepare billing.",
        )
    if not settings.razorpay_key_id.startswith("rzp_test_"):
        raise HTTPException(status_code=422, detail="DealLab permits Razorpay Test Mode keys only.")

    plan = _post(
        "/plans",
        {
            "period": preview.period,
            "interval": 1,
            "item": {"name": f"DealLab: {deal_name}", "amount": preview.amount_subunits, "currency": preview.currency},
            "notes": {"source": "DealLab", "mode": "test", "fixed_recurring_charge_only": "true"},
        },
        settings.razorpay_key_id,
        settings.razorpay_key_secret,
    )
    customer = _post(
        "/customers",
        {"name": customer_name, "notes": {"source": "DealLab", "mode": "test"}},
        settings.razorpay_key_id,
        settings.razorpay_key_secret,
    )
    subscription = _post(
        "/subscriptions",
        {
            "plan_id": plan["id"],
            "customer_id": customer["id"],
            "total_count": preview.total_count,
            "quantity": 1,
            "notes": {"source": "DealLab", "mode": "test", "created_at": datetime.now(timezone.utc).isoformat()},
        },
        settings.razorpay_key_id,
        settings.razorpay_key_secret,
    )
    return {"plan_id": plan["id"], "customer_id": customer["id"], "subscription_id": subscription["id"]}


def _post(path: str, payload: dict, key_id: str, key_secret: str) -> dict:
    credentials = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    request = Request(
        f"{RAZORPAY_API_BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        body = error.read().decode(errors="replace")
        raise HTTPException(status_code=502, detail=f"Razorpay Test Mode rejected the billing setup: {body}") from error
    except URLError as error:
        raise HTTPException(status_code=502, detail=f"Razorpay Test Mode could not be reached: {error.reason}") from error


def _number(value: str) -> float:
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except ValueError:
        return 0
