from enum import Enum

from pydantic import BaseModel, Field

from backend.app.models.economics import CompanyAssumptions
from backend.app.models.intelligence import EffectiveTerm
from backend.app.models.stress import DealHealthSummary


class DealWorkflowStatus(str, Enum):
    draft = "Draft"
    ai_analyzed = "AI Analyzed"
    needs_review = "Needs Review"
    approved_for_simulation = "Approved for Simulation"
    optimized = "Optimized"
    approved_recommendation = "Approved Recommendation"


class TrustTrace(BaseModel):
    contract_evidence: str
    effective_interpretation: str
    scenario_assumption: str
    deterministic_calculation: str
    ai_reasoning_status: str
    confidence: float = Field(ge=0, le=1)


class CandidateChange(BaseModel):
    field_name: str
    original_value: str
    proposed_value: str
    unit: str
    customer_impact: str
    commercial_friction: int = Field(ge=1, le=5)
    rationale: str
    evidence_excerpt: str | None = None
    source_document: str | None = None
    reasoning_status: str = "inferred"
    confidence: float = Field(default=0.82, ge=0, le=1)


class OptimizationOption(BaseModel):
    title: str
    changed_terms: list[CandidateChange]
    current_health: DealHealthSummary
    optimized_health: DealHealthSummary
    financial_improvement: float
    formatted_financial_improvement: str
    formatted_current_annual_exposure: str
    formatted_optimized_annual_exposure: str
    scenarios_fixed: list[str]
    scenarios_still_risky: list[str]
    customer_impact: str
    reasons_for_recommendation: list[str]
    trust_traces: list[TrustTrace]
    score: float


class OptimizeDealRequest(BaseModel):
    terms: list[EffectiveTerm]
    assumptions: CompanyAssumptions
    expected_usage_units: float = Field(ge=0)
    expected_usage_revenue: float = Field(default=0, ge=0)
    max_changed_clauses: int = Field(default=2, ge=1, le=3)


class OptimizeDealResponse(BaseModel):
    current_health: DealHealthSummary
    workflow_status: str = DealWorkflowStatus.optimized
    options: list[OptimizationOption]


class RevisedTermBlock(BaseModel):
    field_name: str
    current: str
    proposed: str
    reason: str
    expected_effect: str
    evidence_excerpt: str | None = None
    source_document: str | None = None
    approval_required: bool = True


class PrepareRevisedTermsRequest(BaseModel):
    option: OptimizationOption


class PrepareRevisedTermsResponse(BaseModel):
    workflow_status: str = DealWorkflowStatus.approved_recommendation
    subject_to_human_approval: bool = True
    revised_terms: list[RevisedTermBlock]
    approval_note: str
