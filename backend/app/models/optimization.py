from pydantic import BaseModel, Field

from backend.app.models.economics import CompanyAssumptions
from backend.app.models.intelligence import EffectiveTerm
from backend.app.models.stress import DealHealthSummary


class CandidateChange(BaseModel):
    field_name: str
    original_value: str
    proposed_value: str
    unit: str
    customer_impact: str
    commercial_friction: int = Field(ge=1, le=5)
    rationale: str


class OptimizationOption(BaseModel):
    title: str
    changed_terms: list[CandidateChange]
    current_health: DealHealthSummary
    optimized_health: DealHealthSummary
    financial_improvement: float
    formatted_financial_improvement: str
    scenarios_fixed: list[str]
    scenarios_still_risky: list[str]
    customer_impact: str
    reasons_for_recommendation: list[str]
    score: float


class OptimizeDealRequest(BaseModel):
    terms: list[EffectiveTerm]
    assumptions: CompanyAssumptions
    expected_usage_units: float = Field(ge=0)
    expected_usage_revenue: float = Field(default=0, ge=0)
    max_changed_clauses: int = Field(default=2, ge=1, le=3)


class OptimizeDealResponse(BaseModel):
    current_health: DealHealthSummary
    options: list[OptimizationOption]
