from pydantic import BaseModel, Field

from backend.app.models.deal import DealAnalysis
from backend.app.models.economics import CompanyAssumptions
from backend.app.models.intelligence import DealIntelligenceResponse


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str


class ContractTextRequest(BaseModel):
    text: str = Field(min_length=20)
    filename: str | None = None


class ContractAnalysisResponse(BaseModel):
    contract_id: int
    deal_terms_id: int
    analysis: DealAnalysis


class DemoDealResponse(BaseModel):
    deal: DealIntelligenceResponse
    assumptions: CompanyAssumptions
    expected_usage_units: float = Field(ge=0)
    expected_usage_revenue: float = Field(ge=0)


class AuditEventResponse(BaseModel):
    id: int
    action: str
    evidence: str
    created_at: str
