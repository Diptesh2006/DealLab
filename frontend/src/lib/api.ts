export type HealthResponse = {
  status: string;
  service: string;
  database: string;
};

export type CommercialTerms = {
  customer_name: string | null;
  annual_contract_value: number;
  term_months: number;
  discount_percent: number;
  usage_commitment: number;
  variable_cost_percent: number;
  support_cost: number;
  payment_terms_days: number;
  auto_renewal: boolean;
  liability_cap_multiplier: number;
};

export type ScenarioResult = {
  scenario_name: string;
  revenue: number;
  cost: number;
  gross_margin: number;
  gross_margin_percent: number;
  downside_exposure: number;
};

export type ContractAnalysisResponse = {
  contract_id: number;
  deal_terms_id: number;
  analysis: {
    terms: CommercialTerms;
    scenarios: ScenarioResult[];
    health_score: number;
    fragile_terms: string[];
    recommendations: string[];
  };
};

export type ReviewStatus =
  | "confirmed"
  | "inferred"
  | "requires_assumption"
  | "requires_human_review";

export type EffectiveTerm = {
  id: number;
  field_name: string;
  normalized_value: string;
  unit: string;
  effective_from: string | null;
  source_document: string | null;
  source_page: number | null;
  evidence_excerpt: string | null;
  confidence: number;
  extraction_type: "explicit" | "inferred" | "unknown";
  review_status: ReviewStatus;
  ambiguous: boolean;
};

export type DealDocument = {
  id: number;
  filename: string;
  document_type: "master_agreement" | "amendment" | "approved_exception";
  precedence_order: number;
};

export type DealIntelligenceResponse = {
  deal_id: number;
  customer_name: string;
  deal_name: string;
  target_gross_margin: number;
  documents: DealDocument[];
  effective_terms: EffectiveTerm[];
};

export type CompanyAssumptions = {
  cost_per_api_call: number;
  monthly_infrastructure_cost: number;
  cost_per_support_hour: number;
  implementation_cost: number;
  minimum_acceptable_gross_margin: number;
  typical_support_consumption_hours: number;
  expected_annual_cost_inflation: number;
};

export type EconomicScenarioInput = {
  name: string;
  expected_usage_units: number;
  usage_revenue: number;
  support_hours?: number | null;
  cost_multiplier?: number;
  apply_temporary_discount: boolean;
  apply_service_credits: boolean;
  apply_rebates: boolean;
  renewal_number: number;
};

export type FinancialLineItem = {
  label: string;
  amount: number;
  formatted_amount: string;
  trace: {
    contract_term: string | null;
    company_assumption: string | null;
    scenario_input: string | null;
  };
};

export type ScenarioEconomicsResult = {
  scenario_name: string;
  currency: string;
  gross_revenue: number;
  effective_revenue_after_discounts: number;
  variable_costs: number;
  support_costs: number;
  credits_penalties: number;
  total_cost: number;
  gross_profit: number;
  gross_margin_percent: number;
  arr: number;
  expected_customer_contribution: number;
  downside_exposure: number;
  difference_from_target_margin: number;
  breakdown: FinancialLineItem[];
};

export type ScenarioSourceLabel =
  | "user-entered assumption"
  | "historical benchmark"
  | "synthetic historical benchmark"
  | "contract-derived"
  | "AI-proposed hypothetical"
  | "system default";

export type ScenarioAssumptionSource = {
  variable: string;
  label: ScenarioSourceLabel;
  detail: string;
};

export type StressScenario = {
  name: string;
  description: string;
  usage_multiplier: number;
  support_hours: number;
  cost_multiplier: number;
  renewal_year: number;
  discount_state: string;
  sla_performance_percent: number | null;
  customer_growth_rate: number;
  relevant_commercial_events: string[];
  sources: ScenarioAssumptionSource[];
  economics_input: EconomicScenarioInput;
};

export type ScenarioStressResult = {
  scenario: StressScenario;
  economics: ScenarioEconomicsResult;
  status: "pass" | "warning" | "critical";
};

export type DealHealthConfig = {
  target_margin_percent: number;
  warning_margin_gap_percent: number;
  critical_margin_gap_percent: number;
  healthy_min_pass_rate: number;
  mostly_healthy_min_pass_rate: number;
  fragile_min_pass_rate: number;
};

export type DealHealthSummary = {
  rating: "Healthy" | "Mostly Healthy" | "Commercially Fragile" | "High Risk";
  percentage_above_target_margin: number;
  expected_scenario_margin: number;
  downside_margin: number;
  worst_case_margin: number;
  estimated_annual_exposure: number;
  critical_scenarios: number;
  warning_scenarios: number;
  calculation_config: DealHealthConfig;
};

export type FailureMode = {
  title: string;
  affected_clause: string;
  scenario: string;
  why_it_fails: string;
  financial_impact: number;
  formatted_financial_impact: string;
  severity: "warning" | "critical";
  confidence: number;
  original_source: string;
  recommended_remediation_category: string;
  explanation: string;
};

export type StressTestResponse = {
  health: DealHealthSummary;
  scenarios: ScenarioStressResult[];
  failure_modes: FailureMode[];
};

export type CandidateChange = {
  field_name: string;
  original_value: string;
  proposed_value: string;
  unit: string;
  customer_impact: string;
  commercial_friction: number;
  rationale: string;
  evidence_excerpt?: string | null;
  source_document?: string | null;
  reasoning_status: string;
  confidence: number;
};

export type TrustTrace = {
  contract_evidence: string;
  effective_interpretation: string;
  scenario_assumption: string;
  deterministic_calculation: string;
  ai_reasoning_status: string;
  confidence: number;
};

export type OptimizationOption = {
  title: string;
  changed_terms: CandidateChange[];
  current_health: DealHealthSummary;
  optimized_health: DealHealthSummary;
  financial_improvement: number;
  formatted_financial_improvement: string;
  formatted_current_annual_exposure: string;
  formatted_optimized_annual_exposure: string;
  scenarios_fixed: string[];
  scenarios_still_risky: string[];
  customer_impact: string;
  reasons_for_recommendation: string[];
  score: number;
  trust_traces: TrustTrace[];
};

export type OptimizeDealResponse = {
  current_health: DealHealthSummary;
  options: OptimizationOption[];
  workflow_status: DealWorkflowStatus;
};

export type DealWorkflowStatus =
  | "Draft"
  | "AI Analyzed"
  | "Needs Review"
  | "Approved for Simulation"
  | "Optimized"
  | "Approved Recommendation";

export type RevisedTermBlock = {
  field_name: string;
  current: string;
  proposed: string;
  reason: string;
  expected_effect: string;
  evidence_excerpt: string;
  approval_required: boolean;
};

export type PrepareRevisedTermsResponse = {
  workflow_status: DealWorkflowStatus;
  subject_to_human_approval: boolean;
  revised_terms: RevisedTermBlock[];
  approval_note: string;
};

export type RazorpayBillingPreview = {
  currency: string;
  amount: number;
  amount_subunits: number;
  period: "monthly" | "yearly";
  total_count: number;
  mapped_terms: string[];
  unsupported_terms: string[];
  note: string;
};

export type RazorpayBillingSetupResponse = {
  deal_id: number;
  mode: "test";
  plan_id: string;
  customer_id: string;
  subscription_id: string;
  preview: RazorpayBillingPreview;
  human_approval_recorded: boolean;
  note: string;
};

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${baseUrl}/api/health`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Backend health check failed: ${response.status}`);
  }

  return response.json();
}

export async function analyzeContractText(text: string, filename?: string): Promise<ContractAnalysisResponse> {
  const response = await fetch(`${baseUrl}/api/contracts/analyze-text`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text, filename }),
  });

  if (!response.ok) {
    throw new Error(`Contract analysis failed: ${response.status}`);
  }

  return response.json();
}

export async function analyzeDeal(formData: FormData): Promise<DealIntelligenceResponse> {
  const response = await fetch(`${baseUrl}/api/deals/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Deal analysis failed: ${response.status}`);
  }

  return response.json();
}

export async function updateEffectiveTerm(
  dealId: number,
  termId: number,
  payload: { normalized_value: string; unit: string; reason: string },
): Promise<EffectiveTerm> {
  const response = await fetch(`${baseUrl}/api/deals/${dealId}/terms/${termId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Manual term edit failed: ${response.status}`);
  }

  const result = await response.json();
  return result.term;
}

export async function evaluateEconomics(payload: {
  terms: EffectiveTerm[];
  assumptions: CompanyAssumptions;
  scenario: EconomicScenarioInput;
}): Promise<ScenarioEconomicsResult> {
  const response = await fetch(`${baseUrl}/api/economics/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Economics evaluation failed: ${response.status}`);
  }

  const result = await response.json();
  return result.result;
}

export async function evaluateStressTest(payload: {
  terms: EffectiveTerm[];
  assumptions: CompanyAssumptions;
  expected_usage_units: number;
  expected_usage_revenue: number;
  health_config?: Partial<DealHealthConfig>;
}): Promise<StressTestResponse> {
  const response = await fetch(`${baseUrl}/api/stress-tests/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Stress test failed: ${response.status}`);
  }

  return response.json();
}

export async function optimizeDeal(payload: {
  terms: EffectiveTerm[];
  assumptions: CompanyAssumptions;
  expected_usage_units: number;
  expected_usage_revenue: number;
  max_changed_clauses?: number;
}): Promise<OptimizeDealResponse> {
  const response = await fetch(`${baseUrl}/api/deals/optimize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Deal optimization failed: ${response.status}`);
  }

  return response.json();
}

export async function prepareRevisedTerms(option: OptimizationOption): Promise<PrepareRevisedTermsResponse> {
  const response = await fetch(`${baseUrl}/api/deals/prepare-revised-terms`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ option }),
  });

  if (!response.ok) {
    throw new Error(`Prepare revised terms failed: ${response.status}`);
  }

  return response.json();
}

export async function prepareRazorpayBilling(
  dealId: number,
  option: OptimizationOption,
): Promise<RazorpayBillingSetupResponse> {
  const response = await fetch(`${baseUrl}/api/deals/${dealId}/billing/razorpay/prepare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ option, human_approved: true }),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Razorpay billing setup failed: ${response.status}`);
  }

  return response.json();
}
