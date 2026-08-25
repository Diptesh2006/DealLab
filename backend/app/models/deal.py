from pydantic import BaseModel, Field


class CommercialTerms(BaseModel):
    customer_name: str | None = None
    annual_contract_value: float = Field(ge=0)
    term_months: int = Field(ge=1)
    discount_percent: float = Field(ge=0, le=100)
    usage_commitment: float = Field(ge=0)
    variable_cost_percent: float = Field(ge=0, le=100)
    support_cost: float = Field(ge=0)
    payment_terms_days: int = Field(ge=0)
    auto_renewal: bool = False
    liability_cap_multiplier: float = Field(ge=0)


class Scenario(BaseModel):
    name: str
    revenue_multiplier: float = Field(gt=0)
    cost_multiplier: float = Field(gt=0)
    support_cost_multiplier: float = Field(gt=0)
    description: str


class ScenarioResult(BaseModel):
    scenario_name: str
    revenue: float
    cost: float
    gross_margin: float
    gross_margin_percent: float
    downside_exposure: float


class DealAnalysis(BaseModel):
    terms: CommercialTerms
    scenarios: list[ScenarioResult]
    health_score: int = Field(ge=0, le=100)
    fragile_terms: list[str]
    recommendations: list[str]
