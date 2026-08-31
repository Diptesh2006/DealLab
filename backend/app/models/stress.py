from enum import Enum

from pydantic import BaseModel, Field

from backend.app.models.economics import CompanyAssumptions, EconomicScenarioInput, ScenarioEconomicsResult
from backend.app.models.intelligence import EffectiveTerm


class ScenarioSourceLabel(str, Enum):
    user_entered_assumption = "user-entered assumption"
    historical_benchmark = "historical benchmark"
    synthetic_historical_benchmark = "synthetic historical benchmark"
    contract_derived = "contract-derived"
    ai_proposed_hypothetical = "AI-proposed hypothetical"
    system_default = "system default"


class ScenarioAssumptionSource(BaseModel):
    variable: str
    label: ScenarioSourceLabel
    detail: str


class StressScenario(BaseModel):
    name: str
    description: str
    usage_multiplier: float = Field(gt=0)
    support_hours: float = Field(ge=0)
    cost_multiplier: float = Field(gt=0)
    renewal_year: int = Field(ge=0)
    discount_state: str
    sla_performance_percent: float | None = Field(default=None, ge=0, le=100)
    customer_growth_rate: float = 0
    relevant_commercial_events: list[str]
    sources: list[ScenarioAssumptionSource]
    economics_input: EconomicScenarioInput


class DealHealthConfig(BaseModel):
    target_margin_percent: float = Field(default=45, ge=0, le=100)
    warning_margin_gap_percent: float = Field(default=5, ge=0)
    critical_margin_gap_percent: float = Field(default=10, ge=0)
    healthy_min_pass_rate: float = Field(default=0.8, ge=0, le=1)
    mostly_healthy_min_pass_rate: float = Field(default=0.6, ge=0, le=1)
    fragile_min_pass_rate: float = Field(default=0.4, ge=0, le=1)


class ScenarioStressResult(BaseModel):
    scenario: StressScenario
    economics: ScenarioEconomicsResult
    status: str


class DealHealthSummary(BaseModel):
    rating: str
    percentage_above_target_margin: float
    expected_scenario_margin: float
    downside_margin: float
    worst_case_margin: float
    estimated_annual_exposure: float
    critical_scenarios: int
    warning_scenarios: int
    calculation_config: DealHealthConfig


class StressTestRequest(BaseModel):
    terms: list[EffectiveTerm]
    assumptions: CompanyAssumptions
    expected_usage_units: float = Field(ge=0)
    expected_usage_revenue: float = Field(default=0, ge=0)
    health_config: DealHealthConfig | None = None


class StressTestResponse(BaseModel):
    health: DealHealthSummary
    scenarios: list[ScenarioStressResult]
