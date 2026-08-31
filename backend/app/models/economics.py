from pydantic import BaseModel, Field

from backend.app.models.intelligence import EffectiveTerm


class CompanyAssumptions(BaseModel):
    cost_per_api_call: float = Field(ge=0)
    monthly_infrastructure_cost: float = Field(ge=0)
    cost_per_support_hour: float = Field(ge=0)
    implementation_cost: float = Field(ge=0)
    minimum_acceptable_gross_margin: float = Field(ge=0, le=100)
    typical_support_consumption_hours: float = Field(ge=0)
    expected_annual_cost_inflation: float = Field(ge=0, le=100)


class EconomicScenarioInput(BaseModel):
    name: str
    expected_usage_units: float = Field(ge=0)
    usage_revenue: float = Field(default=0, ge=0)
    support_hours: float | None = Field(default=None, ge=0)
    apply_temporary_discount: bool = True
    apply_service_credits: bool = False
    apply_rebates: bool = True
    renewal_number: int = Field(default=0, ge=0)


class TraceReference(BaseModel):
    contract_term: str | None = None
    company_assumption: str | None = None
    scenario_input: str | None = None


class FinancialLineItem(BaseModel):
    label: str
    amount: float
    formatted_amount: str
    trace: TraceReference


class ScenarioEconomicsResult(BaseModel):
    scenario_name: str
    currency: str
    gross_revenue: float
    effective_revenue_after_discounts: float
    variable_costs: float
    support_costs: float
    credits_penalties: float
    total_cost: float
    gross_profit: float
    gross_margin_percent: float
    arr: float
    expected_customer_contribution: float
    downside_exposure: float
    difference_from_target_margin: float
    breakdown: list[FinancialLineItem]


class EconomicsEvaluationRequest(BaseModel):
    terms: list[EffectiveTerm]
    assumptions: CompanyAssumptions
    scenario: EconomicScenarioInput


class EconomicsEvaluationResponse(BaseModel):
    result: ScenarioEconomicsResult
