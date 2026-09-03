from typing import Literal

from pydantic import BaseModel, Field

from backend.app.models.optimization import OptimizationOption


class RazorpayBillingPreview(BaseModel):
    currency: str
    amount: int = Field(ge=1)
    amount_subunits: int = Field(ge=1)
    period: Literal["monthly", "yearly"]
    total_count: int = Field(ge=1)
    mapped_terms: list[str]
    unsupported_terms: list[str]
    note: str


class PrepareRazorpayBillingRequest(BaseModel):
    option: OptimizationOption
    human_approved: Literal[True]


class RazorpayBillingSetupResponse(BaseModel):
    deal_id: int
    mode: Literal["test"] = "test"
    plan_id: str
    customer_id: str
    subscription_id: str
    preview: RazorpayBillingPreview
    human_approval_recorded: bool = True
    note: str
