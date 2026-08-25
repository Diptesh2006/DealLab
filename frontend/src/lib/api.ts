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
