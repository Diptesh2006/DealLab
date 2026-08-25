from pydantic import BaseModel, Field

from backend.app.models.deal import DealAnalysis


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
