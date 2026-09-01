"use client";

import { CheckCircle2, FileText, Loader2, Save, Send, ShieldCheck, Upload } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  analyzeDeal,
  evaluateEconomics,
  evaluateStressTest,
  optimizeDeal,
  prepareRevisedTerms,
  updateEffectiveTerm,
  type CompanyAssumptions,
  type DealWorkflowStatus,
  type DealIntelligenceResponse,
  type EconomicScenarioInput,
  type EffectiveTerm,
  type ReviewStatus,
  type ScenarioEconomicsResult,
  type ScenarioStressResult,
  type StressTestResponse,
  type OptimizeDealResponse,
  type OptimizationOption,
  type PrepareRevisedTermsResponse,
} from "@/lib/api";

type EditableTerm = EffectiveTerm & {
  draftValue: string;
  draftUnit: string;
  isSaving?: boolean;
};

const statusStyles: Record<ReviewStatus, string> = {
  confirmed: "border-mint/40 bg-mint/10 text-ink",
  inferred: "border-amber/50 bg-amber/10 text-ink",
  requires_assumption: "border-orange-400 bg-orange-50 text-orange-900",
  requires_human_review: "border-red-300 bg-red-50 text-red-900",
};

export function DealAnalyzer() {
  const [customerName, setCustomerName] = useState("Globex");
  const [dealName, setDealName] = useState("Global API Platform Renewal");
  const [targetGrossMargin, setTargetGrossMargin] = useState("55");
  const [internalCostAssumptions, setInternalCostAssumptions] = useState("Support cost sensitivity enabled");
  const [mainContract, setMainContract] = useState<File | null>(null);
  const [amendments, setAmendments] = useState<File[]>([]);
  const [exceptionNotes, setExceptionNotes] = useState<File[]>([]);
  const [deal, setDeal] = useState<DealIntelligenceResponse | null>(null);
  const [terms, setTerms] = useState<EditableTerm[]>([]);
  const [assumptions, setAssumptions] = useState<CompanyAssumptions>({
    cost_per_api_call: 0.2,
    monthly_infrastructure_cost: 60000,
    cost_per_support_hour: 1000,
    implementation_cost: 200000,
    minimum_acceptable_gross_margin: 45,
    typical_support_consumption_hours: 550,
    expected_annual_cost_inflation: 0,
  });
  const [scenario, setScenario] = useState<EconomicScenarioInput>({
    name: "Expected case",
    expected_usage_units: 1200000,
    usage_revenue: 240000,
    support_hours: null,
    apply_temporary_discount: true,
    apply_service_credits: true,
    apply_rebates: true,
    renewal_number: 1,
  });
  const [economics, setEconomics] = useState<ScenarioEconomicsResult | null>(null);
  const [stressTest, setStressTest] = useState<StressTestResponse | null>(null);
  const [optimization, setOptimization] = useState<OptimizeDealResponse | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<DealWorkflowStatus>("Draft");
  const [revisedTerms, setRevisedTerms] = useState<PrepareRevisedTermsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isStressTesting, setIsStressTesting] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const unresolvedCount = useMemo(
    () => terms.filter((term) => term.review_status === "requires_human_review" || term.ambiguous).length,
    [terms],
  );

  const canApproveForSimulation = terms.length > 0 && unresolvedCount === 0;

  async function submit() {
    if (!mainContract) {
      setError("Main contract is required.");
      return;
    }

    const formData = new FormData();
    formData.append("customer_name", customerName);
    formData.append("deal_name", dealName);
    formData.append("target_gross_margin", targetGrossMargin);
    formData.append("internal_cost_assumptions", internalCostAssumptions);
    formData.append("main_contract", mainContract);
    amendments.forEach((file) => formData.append("amendments", file));
    exceptionNotes.forEach((file) => formData.append("exception_notes", file));

    setIsLoading(true);
    setError(null);

    try {
      const result = await analyzeDeal(formData);
      setDeal(result);
      setTerms(result.effective_terms.map(toEditableTerm));
      setEconomics(null);
      setStressTest(null);
      setOptimization(null);
      setRevisedTerms(null);
      setWorkflowStatus(hasReviewIssues(result.effective_terms) ? "Needs Review" : "AI Analyzed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deal analysis failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function saveTerm(term: EditableTerm) {
    if (!deal || !term.id) return;

    setTerms((current) => current.map((item) => (item.id === term.id ? { ...item, isSaving: true } : item)));
    try {
      const updated = await updateEffectiveTerm(deal.deal_id, term.id, {
        normalized_value: term.draftValue,
        unit: term.draftUnit,
        reason: "Edited on Deal Terms Review screen",
      });
      setTerms((current) => current.map((item) => (item.id === term.id ? toEditableTerm(updated) : item)));
      setWorkflowStatus(hasReviewIssues(terms.map((item) => (item.id === term.id ? toEditableTerm(updated) : item))) ? "Needs Review" : "AI Analyzed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Manual edit failed");
      setTerms((current) => current.map((item) => (item.id === term.id ? { ...item, isSaving: false } : item)));
    }
  }

  async function calculateEconomics() {
    if (!terms.length) return;

    setIsEvaluating(true);
    setError(null);
    try {
      const result = await evaluateEconomics({
        terms: terms.map(fromEditableTerm),
        assumptions,
        scenario,
      });
      setEconomics(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Economics evaluation failed");
    } finally {
      setIsEvaluating(false);
    }
  }

  async function runStressTest() {
    if (!terms.length) return;

    setIsStressTesting(true);
    setError(null);
    try {
      const result = await evaluateStressTest({
        terms: terms.map(fromEditableTerm),
        assumptions,
        expected_usage_units: scenario.expected_usage_units,
        expected_usage_revenue: scenario.usage_revenue,
        health_config: {
          target_margin_percent: assumptions.minimum_acceptable_gross_margin,
        },
      });
      setStressTest(result);
      setOptimization(null);
      setRevisedTerms(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stress test failed");
    } finally {
      setIsStressTesting(false);
    }
  }

  async function runOptimization() {
    if (!terms.length) return;

    setIsOptimizing(true);
    setError(null);
    try {
      const result = await optimizeDeal({
        terms: terms.map(fromEditableTerm),
        assumptions,
        expected_usage_units: scenario.expected_usage_units,
        expected_usage_revenue: scenario.usage_revenue,
        max_changed_clauses: 2,
      });
      setOptimization(result);
      setRevisedTerms(null);
      setWorkflowStatus(result.workflow_status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deal optimization failed");
    } finally {
      setIsOptimizing(false);
    }
  }

  async function prepareTermsArtifact(option: OptimizationOption) {
    setIsOptimizing(true);
    setError(null);
    try {
      const result = await prepareRevisedTerms(option);
      setRevisedTerms(result);
      setWorkflowStatus(result.workflow_status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prepare revised terms failed");
    } finally {
      setIsOptimizing(false);
    }
  }

  return (
    <section className="mx-auto grid max-w-7xl gap-6 px-6 py-8 xl:grid-cols-[380px_1fr]">
      <form className="rounded-md border border-ink/10 bg-white p-5" onSubmit={(event) => event.preventDefault()}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-steel">New deal</p>
            <h2 className="text-xl font-semibold text-ink">Contract package</h2>
          </div>
          <Upload className="text-mint" size={24} />
        </div>

        <div className="space-y-4">
          <Field label="Customer">
            <input className="input" value={customerName} onChange={(event) => setCustomerName(event.target.value)} />
          </Field>
          <Field label="Deal name">
            <input className="input" value={dealName} onChange={(event) => setDealName(event.target.value)} />
          </Field>
          <Field label="Target gross margin">
            <input
              className="input"
              min="0"
              max="100"
              type="number"
              value={targetGrossMargin}
              onChange={(event) => setTargetGrossMargin(event.target.value)}
            />
          </Field>
          <Field label="Internal cost assumptions">
            <textarea
              className="input min-h-20 resize-y"
              value={internalCostAssumptions}
              onChange={(event) => setInternalCostAssumptions(event.target.value)}
            />
          </Field>
          <FileField
            label="Main contract"
            multiple={false}
            onChange={(files) => setMainContract(files[0] ?? null)}
            selected={mainContract ? [mainContract] : []}
          />
          <FileField label="Amendments" multiple onChange={setAmendments} selected={amendments} />
          <FileField label="Approved exceptions" multiple onChange={setExceptionNotes} selected={exceptionNotes} />
        </div>

        <button
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-mint px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
          onClick={submit}
          disabled={isLoading || !customerName || !dealName || !mainContract}
        >
          {isLoading ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
          Analyze Deal
        </button>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      </form>

      <div className="rounded-md border border-ink/10 bg-white">
        <div className="flex flex-col gap-3 border-b border-ink/10 p-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-steel">Deal Terms Review</p>
            <h2 className="text-xl font-semibold text-ink">
              {deal ? `${deal.customer_name} - ${deal.deal_name}` : "Awaiting extraction"}
            </h2>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <span className="rounded-md border border-ink/10 bg-paper px-2 py-1 text-ink">
              {workflowStatus}
            </span>
            <span className="rounded-md border border-mint/40 bg-mint/10 px-2 py-1">Confirmed</span>
            <span className="rounded-md border border-amber/50 bg-amber/10 px-2 py-1">Inferred</span>
            <span className="rounded-md border border-red-300 bg-red-50 px-2 py-1">{unresolvedCount} unresolved</span>
          </div>
        </div>

        {terms.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] border-collapse text-left text-sm">
              <thead className="bg-ink/5 text-xs uppercase tracking-wide text-steel">
                <tr>
                  <th className="px-3 py-3">Term</th>
                  <th className="px-3 py-3">Value</th>
                  <th className="px-3 py-3">Unit</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Effective</th>
                  <th className="px-3 py-3">Evidence</th>
                  <th className="px-3 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {terms.map((term) => (
                  <tr key={term.id} className="border-t border-ink/10 align-top">
                    <td className="px-3 py-3 font-medium text-ink">{humanize(term.field_name)}</td>
                    <td className="px-3 py-3">
                      <input
                        className="input min-w-36"
                        value={term.draftValue}
                        onChange={(event) => updateDraft(term.id, "draftValue", event.target.value, setTerms)}
                      />
                    </td>
                    <td className="px-3 py-3">
                      <input
                        className="input min-w-32"
                        value={term.draftUnit}
                        onChange={(event) => updateDraft(term.id, "draftUnit", event.target.value, setTerms)}
                      />
                    </td>
                    <td className="px-3 py-3">
                      <span className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${statusStyles[term.review_status]}`}>
                        {humanize(term.review_status)}
                      </span>
                      <p className="mt-1 text-xs text-steel">
                        {term.extraction_type} - {Math.round(term.confidence * 100)}%
                      </p>
                    </td>
                    <td className="px-3 py-3 text-steel">{term.effective_from ?? "current"}</td>
                    <td className="max-w-80 px-3 py-3 text-steel">
                      <p className="font-medium text-ink">{term.source_document ?? "missing"}</p>
                      <p className="line-clamp-3">{term.evidence_excerpt ?? "requires_human_review"}</p>
                    </td>
                    <td className="px-3 py-3">
                      <button
                        className="inline-flex items-center gap-2 rounded-md border border-ink/15 px-3 py-2 text-xs font-semibold text-ink disabled:opacity-60"
                        onClick={() => saveTerm(term)}
                        disabled={term.isSaving || (term.draftValue === term.normalized_value && term.draftUnit === term.unit)}
                      >
                        {term.isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                        Save
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex min-h-96 items-center justify-center bg-paper p-6 text-sm text-steel">
            <div className="max-w-sm text-center">
              <FileText className="mx-auto mb-3 text-mint" size={28} />
              Upload a contract package to extract the currently effective commercial state.
            </div>
          </div>
        )}

        {terms.length ? (
          <div className="border-t border-ink/10 p-5">
            <div className="grid gap-5 lg:grid-cols-2">
              <div>
                <p className="text-sm font-medium uppercase tracking-wide text-steel">Company assumptions</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <NumberField label="Cost per API call" value={assumptions.cost_per_api_call} onChange={(value) => setAssumptions({ ...assumptions, cost_per_api_call: value })} />
                  <NumberField label="Monthly infrastructure" value={assumptions.monthly_infrastructure_cost} onChange={(value) => setAssumptions({ ...assumptions, monthly_infrastructure_cost: value })} />
                  <NumberField label="Cost per support hour" value={assumptions.cost_per_support_hour} onChange={(value) => setAssumptions({ ...assumptions, cost_per_support_hour: value })} />
                  <NumberField label="Implementation cost" value={assumptions.implementation_cost} onChange={(value) => setAssumptions({ ...assumptions, implementation_cost: value })} />
                  <NumberField label="Minimum margin %" value={assumptions.minimum_acceptable_gross_margin} onChange={(value) => setAssumptions({ ...assumptions, minimum_acceptable_gross_margin: value })} />
                  <NumberField label="Support hours" value={assumptions.typical_support_consumption_hours} onChange={(value) => setAssumptions({ ...assumptions, typical_support_consumption_hours: value })} />
                  <NumberField label="Annual cost inflation %" value={assumptions.expected_annual_cost_inflation} onChange={(value) => setAssumptions({ ...assumptions, expected_annual_cost_inflation: value })} />
                </div>
              </div>

              <div>
                <p className="text-sm font-medium uppercase tracking-wide text-steel">Scenario input</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Field label="Scenario name">
                    <input className="input" value={scenario.name} onChange={(event) => setScenario({ ...scenario, name: event.target.value })} />
                  </Field>
                  <NumberField label="Expected usage units" value={scenario.expected_usage_units} onChange={(value) => setScenario({ ...scenario, expected_usage_units: value })} />
                  <NumberField label="Usage revenue" value={scenario.usage_revenue} onChange={(value) => setScenario({ ...scenario, usage_revenue: value })} />
                  <NumberField label="Renewal number" value={scenario.renewal_number} onChange={(value) => setScenario({ ...scenario, renewal_number: value })} />
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-sm text-ink">
                  <Toggle label="Temporary discount" checked={scenario.apply_temporary_discount} onChange={(checked) => setScenario({ ...scenario, apply_temporary_discount: checked })} />
                  <Toggle label="Service credits" checked={scenario.apply_service_credits} onChange={(checked) => setScenario({ ...scenario, apply_service_credits: checked })} />
                  <Toggle label="Rebates" checked={scenario.apply_rebates} onChange={(checked) => setScenario({ ...scenario, apply_rebates: checked })} />
                </div>
                <button
                  className="mr-2 mt-4 inline-flex items-center gap-2 rounded-md border border-mint/40 bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
                  onClick={() => setWorkflowStatus("Approved for Simulation")}
                  disabled={!canApproveForSimulation}
                  title={canApproveForSimulation ? "Mark reviewed terms approved for simulation" : "Resolve ambiguous or human-review terms first"}
                >
                  <ShieldCheck size={16} />
                  Approve for Simulation
                </button>
                <button
                  className="mt-4 inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  onClick={calculateEconomics}
                  disabled={isEvaluating}
                >
                  {isEvaluating ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Calculate Economics
                </button>
                <button
                  className="ml-2 mt-4 inline-flex items-center gap-2 rounded-md bg-amber px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
                  onClick={runStressTest}
                  disabled={isStressTesting}
                >
                  {isStressTesting ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Run Stress Test
                </button>
                <button
                  className="ml-2 mt-4 inline-flex items-center gap-2 rounded-md bg-mint px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
                  onClick={runOptimization}
                  disabled={isOptimizing}
                >
                  {isOptimizing ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Optimize Deal
                </button>
              </div>
            </div>

            {economics ? <EconomicsResult result={economics} /> : null}
            {optimization ? (
              <OptimizationResult
                result={optimization}
                revisedTerms={revisedTerms}
                onPrepare={prepareTermsArtifact}
                isPreparing={isOptimizing}
              />
            ) : null}
            {stressTest ? <StressTestResult result={stressTest} deal={deal} /> : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-steel">{label}</span>
      {children}
    </label>
  );
}

function FileField({
  label,
  multiple,
  onChange,
  selected,
}: {
  label: string;
  multiple: boolean;
  onChange: (files: File[]) => void;
  selected: File[];
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-steel">{label}</span>
      <input
        className="block w-full text-sm text-steel file:mr-3 file:rounded-md file:border-0 file:bg-ink file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white"
        type="file"
        accept=".pdf,.txt"
        multiple={multiple}
        onChange={(event) => onChange(Array.from(event.target.files ?? []))}
      />
      {selected.length ? (
        <p className="mt-1 truncate text-xs text-steel">{selected.map((file) => file.name).join(", ")}</p>
      ) : null}
    </label>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <Field label={label}>
      <input className="input" type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </Field>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="inline-flex items-center gap-2 rounded-md border border-ink/10 px-3 py-2">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function EconomicsResult({ result }: { result: ScenarioEconomicsResult }) {
  return (
    <div className="mt-6 rounded-md border border-ink/10 bg-paper p-4">
      <div className="grid gap-3 sm:grid-cols-4">
        <SummaryMetric label="Gross revenue" value={result.gross_revenue} currency={result.currency} />
        <SummaryMetric label="Effective revenue" value={result.effective_revenue_after_discounts} currency={result.currency} />
        <SummaryMetric label="Gross margin" value={`${result.gross_margin_percent}%`} />
        <SummaryMetric label="Downside exposure" value={result.downside_exposure} currency={result.currency} />
      </div>

      <details className="mt-4 rounded-md border border-ink/10 bg-white">
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-ink">
          Calculation trace for {result.scenario_name}
        </summary>
        <div className="overflow-x-auto border-t border-ink/10">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-ink/5 text-xs uppercase tracking-wide text-steel">
              <tr>
                <th className="px-3 py-2">Line item</th>
                <th className="px-3 py-2">Amount</th>
                <th className="px-3 py-2">Contract term</th>
                <th className="px-3 py-2">Assumption</th>
                <th className="px-3 py-2">Scenario input</th>
              </tr>
            </thead>
            <tbody>
              {result.breakdown.map((item) => (
                <tr key={item.label} className="border-t border-ink/10">
                  <td className="px-3 py-2 font-medium text-ink">{item.label}</td>
                  <td className="px-3 py-2 text-ink">{item.formatted_amount}</td>
                  <td className="px-3 py-2 text-steel">{item.trace.contract_term ?? "-"}</td>
                  <td className="px-3 py-2 text-steel">{item.trace.company_assumption ?? "-"}</td>
                  <td className="px-3 py-2 text-steel">{item.trace.scenario_input ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

function StressTestResult({ result, deal }: { result: StressTestResponse; deal: DealIntelligenceResponse | null }) {
  const currency = result.scenarios[0]?.economics.currency ?? "USD";
  const chartData = result.scenarios.map((item) => ({
    name: item.scenario.name,
    margin: item.economics.gross_margin_percent,
    exposure: item.economics.downside_exposure,
    status: item.status,
  }));

  return (
    <div className="mt-6 space-y-5">
      <section className="rounded-md border border-ink/10 bg-ink p-5 text-white">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-mint">Deal Health</p>
            <h2 className="mt-1 text-2xl font-semibold">
              {deal ? `${deal.customer_name} ${deal.deal_name}` : "Enterprise Contract"}
            </h2>
            <p className="mt-3 text-sm uppercase tracking-wide text-white/70">Status</p>
            <p className="text-2xl font-semibold uppercase text-amber">{result.health.rating}</p>
          </div>
          <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
            <HealthStat label="ARR" value={formatCompactMoney(result.scenarios.find((item) => item.scenario.name === "Expected adoption")?.economics.arr ?? 0, currency)} />
            <HealthStat label="Target Gross Margin" value={`${result.health.calculation_config.target_margin_percent}%`} />
            <HealthStat label="Expected Margin" value={`${result.health.expected_scenario_margin}%`} />
            <HealthStat label="Downside Margin" value={`${result.health.downside_margin}%`} />
            <HealthStat label="Scenarios Healthy" value={`${result.health.percentage_above_target_margin}%`} />
            <HealthStat label="Annual Value at Risk" value={formatCompactMoney(result.health.estimated_annual_exposure, currency)} />
          </div>
        </div>
        <p className="mt-4 text-xs leading-5 text-white/65">
          Rating uses configurable thresholds: target margin {result.health.calculation_config.target_margin_percent}%,
          warning gap {result.health.calculation_config.warning_margin_gap_percent}%, critical gap{" "}
          {result.health.calculation_config.critical_margin_gap_percent}%.
        </p>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_0.8fr]">
        <div className="rounded-md border border-ink/10 bg-white p-4">
          <p className="text-sm font-medium uppercase tracking-wide text-steel">Scenario outcome chart</p>
          <div className="mt-3 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={70} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <ReferenceLine y={result.health.calculation_config.target_margin_percent} stroke="#17202a" strokeDasharray="4 4" />
                <Bar dataKey="margin" name="Gross margin %">
                  {chartData.map((item) => (
                    <Cell key={item.name} fill={statusColor(item.status)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-md border border-ink/10 bg-white p-4">
          <p className="text-sm font-medium uppercase tracking-wide text-steel">Margin distribution</p>
          <div className="mt-3 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="margin" name="Margin %" tick={{ fontSize: 11 }} />
                <YAxis dataKey="exposure" name="Exposure" tick={{ fontSize: 11 }} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                <ReferenceLine x={result.health.calculation_config.target_margin_percent} stroke="#17202a" strokeDasharray="4 4" />
                <Scatter data={chartData} fill="#2fbf9b" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {result.failure_modes.map((mode) => (
          <article key={`${mode.title}-${mode.scenario}`} className="rounded-md border border-ink/10 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-steel">{mode.scenario}</p>
                <h3 className="mt-1 text-lg font-semibold text-ink">{mode.title}</h3>
              </div>
              <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${mode.severity === "critical" ? "border-red-300 bg-red-50 text-red-900" : "border-amber/50 bg-amber/10 text-ink"}`}>
                {mode.severity}
              </span>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <SummaryMetric label="Impact" value={mode.financial_impact} currency={currency} />
              <SummaryMetric label="Confidence" value={`${Math.round(mode.confidence * 100)}%`} />
              <SummaryMetric label="Source" value={mode.original_source} />
            </div>
            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="font-semibold text-steel">Affected clause</dt>
                <dd className="text-ink">{mode.affected_clause}</dd>
              </div>
              <div>
                <dt className="font-semibold text-steel">Why it fails</dt>
                <dd className="text-ink">{mode.why_it_fails}</dd>
              </div>
              <div>
                <dt className="font-semibold text-steel">Recommended remediation</dt>
                <dd className="text-ink">{mode.recommended_remediation_category}</dd>
              </div>
            </dl>
            <p className="mt-4 rounded-md bg-paper p-3 text-sm leading-6 text-ink">{mode.explanation}</p>
          </article>
        ))}
      </section>

      <section className="rounded-md border border-ink/10 bg-white">
        <div className="border-b border-ink/10 p-4">
          <p className="text-sm font-medium uppercase tracking-wide text-steel">Scenario comparison</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1120px] text-left text-sm">
            <thead className="bg-ink/5 text-xs uppercase tracking-wide text-steel">
              <tr>
                <th className="px-3 py-3">Scenario</th>
                <th className="px-3 py-3">Variables</th>
                <th className="px-3 py-3">Sources</th>
                <th className="px-3 py-3">Margin</th>
                <th className="px-3 py-3">Exposure</th>
                <th className="px-3 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {result.scenarios.map((item) => (
                <StressScenarioRow key={item.scenario.name} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function OptimizationResult({
  result,
  revisedTerms,
  onPrepare,
  isPreparing,
}: {
  result: OptimizeDealResponse;
  revisedTerms: PrepareRevisedTermsResponse | null;
  onPrepare: (option: OptimizationOption) => void;
  isPreparing: boolean;
}) {
  const best = result.options[0];

  if (!best) {
    return (
      <section className="mt-6 rounded-md border border-ink/10 bg-white p-5">
        <p className="text-sm font-medium uppercase tracking-wide text-steel">Optimize Deal</p>
        <h2 className="mt-1 text-xl font-semibold text-ink">No bounded improvement found</h2>
        <p className="mt-2 text-sm leading-6 text-steel">
          The optimizer did not find a practical one- or two-clause change that improves stress-test resilience.
        </p>
      </section>
    );
  }

  return (
    <section className="mt-6 rounded-md border border-ink/10 bg-white">
      <div className="border-b border-ink/10 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-steel">Optimize Deal</p>
            <h2 className="mt-1 text-xl font-semibold text-ink">{best.title}</h2>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-md border border-mint/40 bg-mint/10 px-3 py-2 text-xs font-semibold text-ink">
            <CheckCircle2 size={14} />
            {result.workflow_status}
          </span>
        </div>
        <p className="mt-2 text-sm leading-6 text-steel">
          Ranked by deterministic stress-test improvement, customer impact, clause count, commercial friction, and deviation from the original deal.
        </p>
      </div>

      <div className="grid gap-4 p-5 lg:grid-cols-2">
        <DealState title="Current Deal" health={best.current_health} formattedExposure={best.formatted_current_annual_exposure} />
        <DealState title="Optimized Deal" health={best.optimized_health} formattedExposure={best.formatted_optimized_annual_exposure} highlighted />
      </div>

      <div className="grid gap-4 border-t border-ink/10 p-5 lg:grid-cols-[1fr_0.8fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-steel">Changed terms</p>
          <div className="mt-3 space-y-3">
            {best.changed_terms.map((change) => (
              <div key={change.field_name} className="rounded-md border border-mint/30 bg-mint/10 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-semibold text-ink">{humanize(change.field_name)}</p>
                  <span className="rounded-md border border-ink/10 bg-white px-2 py-1 text-xs text-steel">
                    friction {change.commercial_friction}/5
                  </span>
                </div>
                <div className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                  <div className="rounded-md bg-white p-2">
                    <p className="text-xs uppercase tracking-wide text-steel">Original</p>
                    <p className="font-medium text-ink">{change.original_value} {change.unit}</p>
                  </div>
                  <div className="rounded-md bg-white p-2">
                    <p className="text-xs uppercase tracking-wide text-steel">Proposed</p>
                    <p className="font-medium text-ink">{change.proposed_value} {change.unit}</p>
                  </div>
                </div>
                <p className="mt-2 text-sm leading-6 text-ink">{change.rationale}</p>
                <p className="mt-2 text-xs leading-5 text-steel">
                  Evidence: {change.evidence_excerpt ?? "requires_human_review"}{" "}
                  {change.source_document ? `(${change.source_document})` : ""}
                </p>
                <p className="mt-1 text-xs text-steel">
                  AI reasoning status: {humanize(change.reasoning_status)}; extraction confidence{" "}
                  {Math.round(change.confidence * 100)}%
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <SummaryMetric label="Financial improvement" value={best.formatted_financial_improvement} />
          <SummaryMetric label="Customer impact" value={best.customer_impact} />
          <ListPanel title="Scenarios fixed" items={best.scenarios_fixed} empty="No scenarios fully fixed." />
          <ListPanel title="Still risky" items={best.scenarios_still_risky} empty="No risky scenarios remain." />
          <ListPanel title="Reasons" items={best.reasons_for_recommendation} empty="No ranking reasons returned." />
          <button
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            onClick={() => onPrepare(best)}
            disabled={isPreparing}
          >
            {isPreparing ? <Loader2 className="animate-spin" size={16} /> : <ShieldCheck size={16} />}
            Prepare Revised Terms
          </button>
        </div>
      </div>

      <div className="border-t border-ink/10 p-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-steel">Trust trace</p>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {best.trust_traces.map((trace) => (
            <div key={`${trace.effective_interpretation}-${trace.scenario_assumption}`} className="rounded-md border border-ink/10 bg-paper p-3 text-sm">
              <p className="font-semibold text-ink">Contract evidence</p>
              <p className="mt-1 text-steel">{trace.contract_evidence}</p>
              <p className="mt-3 font-semibold text-ink">Effective interpretation</p>
              <p className="mt-1 text-steel">{trace.effective_interpretation}</p>
              <p className="mt-3 font-semibold text-ink">Scenario assumption</p>
              <p className="mt-1 text-steel">{trace.scenario_assumption}</p>
              <p className="mt-3 font-semibold text-ink">Deterministic calculation</p>
              <p className="mt-1 text-steel">{trace.deterministic_calculation}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-steel">
                {humanize(trace.ai_reasoning_status)} - {Math.round(trace.confidence * 100)}% extraction confidence
              </p>
            </div>
          ))}
        </div>
      </div>

      {revisedTerms ? (
        <div className="border-t border-ink/10 bg-paper p-5">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <p className="text-sm font-semibold uppercase tracking-wide text-steel">Prepared revised terms</p>
            <span className="rounded-md border border-amber/50 bg-amber/10 px-3 py-1 text-xs font-semibold text-ink">
              Subject to human approval
            </span>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            {revisedTerms.revised_terms.map((term) => (
              <div key={term.field_name} className="rounded-md border border-ink/10 bg-white p-3 text-sm">
                <p className="font-semibold text-ink">{humanize(term.field_name)}</p>
                <p className="mt-2"><span className="font-semibold text-steel">Current:</span> {term.current}</p>
                <p className="mt-1"><span className="font-semibold text-steel">Proposed:</span> {term.proposed}</p>
                <p className="mt-3"><span className="font-semibold text-steel">Reason:</span> {term.reason}</p>
                <p className="mt-1"><span className="font-semibold text-steel">Expected effect:</span> {term.expected_effect}</p>
                <p className="mt-3 text-xs leading-5 text-steel">Evidence: {term.evidence_excerpt}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 rounded-md border border-amber/50 bg-white p-3 text-sm leading-6 text-ink">
            {revisedTerms.approval_note}
          </p>
        </div>
      ) : null}

      {result.options.length > 1 ? (
        <div className="border-t border-ink/10 p-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-steel">Alternative options</p>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            {result.options.slice(1).map((option) => (
              <OptionSummary key={option.title} option={option} />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function DealState({
  title,
  health,
  formattedExposure,
  highlighted = false,
}: {
  title: string;
  health: OptimizationOption["current_health"];
  formattedExposure: string;
  highlighted?: boolean;
}) {
  return (
    <div className={`rounded-md border p-4 ${highlighted ? "border-mint/40 bg-mint/10" : "border-ink/10 bg-paper"}`}>
      <p className="text-sm font-semibold uppercase tracking-wide text-steel">{title}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <SummaryMetric label="Rating" value={health.rating} />
        <SummaryMetric label="Healthy scenarios" value={`${health.percentage_above_target_margin}%`} />
        <SummaryMetric label="Expected margin" value={`${health.expected_scenario_margin}%`} />
        <SummaryMetric label="Downside margin" value={`${health.downside_margin}%`} />
        <SummaryMetric label="Annual exposure" value={formattedExposure} />
        <SummaryMetric label="Critical" value={health.critical_scenarios} />
      </div>
    </div>
  );
}

function ListPanel({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="rounded-md border border-ink/10 bg-paper p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-steel">{title}</p>
      <ul className="mt-2 space-y-1 text-sm text-ink">
        {(items.length ? items : [empty]).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function OptionSummary({ option }: { option: OptimizationOption }) {
  return (
    <div className="rounded-md border border-ink/10 bg-paper p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold text-ink">{option.title}</p>
        <span className="text-xs font-semibold text-steel">score {option.score}</span>
      </div>
      <p className="mt-2 text-sm text-steel">
        Healthy scenarios {option.current_health.percentage_above_target_margin}% to{" "}
        {option.optimized_health.percentage_above_target_margin}%; exposure improvement{" "}
        {option.formatted_financial_improvement}.
      </p>
    </div>
  );
}

function StressScenarioRow({ item }: { item: ScenarioStressResult }) {
  const statusClass = {
    pass: "border-mint/40 bg-mint/10 text-ink",
    warning: "border-amber/50 bg-amber/10 text-ink",
    critical: "border-red-300 bg-red-50 text-red-900",
  }[item.status];

  return (
    <tr className="border-t border-ink/10 align-top">
      <td className="px-3 py-3">
        <details>
          <summary className="cursor-pointer font-semibold text-ink">{item.scenario.name}</summary>
          <p className="mt-2 max-w-72 text-xs leading-5 text-steel">{item.scenario.description}</p>
          <div className="mt-2 rounded-md bg-paper p-2 text-xs text-steel">
            {item.economics.breakdown.map((line) => (
              <div key={line.label} className="flex justify-between gap-3 py-0.5">
                <span>{line.label}</span>
                <span className="font-medium text-ink">{line.formatted_amount}</span>
              </div>
            ))}
          </div>
        </details>
      </td>
      <td className="px-3 py-3 text-xs leading-5 text-steel">
        <p>Usage x{item.scenario.usage_multiplier}</p>
        <p>Support {item.scenario.support_hours}h</p>
        <p>Cost x{item.scenario.cost_multiplier}</p>
        <p>Renewal year {item.scenario.renewal_year}</p>
        <p>SLA {item.scenario.sla_performance_percent ?? "-"}%</p>
        <p>Growth {Math.round(item.scenario.customer_growth_rate * 100)}%</p>
        <p>{item.scenario.discount_state}</p>
      </td>
      <td className="px-3 py-3">
        <div className="flex max-w-72 flex-wrap gap-1">
          {item.scenario.sources.map((source) => (
            <span key={`${source.variable}-${source.label}`} title={source.detail} className="rounded-md border border-ink/10 bg-paper px-2 py-1 text-xs text-steel">
              {source.label}
            </span>
          ))}
        </div>
        <p className="mt-2 max-w-72 text-xs text-steel">{item.scenario.relevant_commercial_events.join(", ")}</p>
      </td>
      <td className="px-3 py-3 font-semibold text-ink">{item.economics.gross_margin_percent}%</td>
      <td className="px-3 py-3 text-ink">{formatMoney(item.economics.downside_exposure, item.economics.currency)}</td>
      <td className="px-3 py-3">
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${statusClass}`}>{item.status}</span>
      </td>
    </tr>
  );
}

function SummaryMetric({
  label,
  value,
  currency,
}: {
  label: string;
  value: number | string;
  currency?: string;
}) {
  const display = typeof value === "number" && currency ? new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value) : value;

  return (
    <div className="rounded-md border border-ink/10 bg-white p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-steel">{label}</p>
      <p className="mt-1 text-lg font-semibold text-ink">{display}</p>
    </div>
  );
}

function HealthStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-white/55">{label}</p>
      <p className="mt-1 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

function statusColor(status: ScenarioStressResult["status"]) {
  if (status === "critical") return "#dc2626";
  if (status === "warning") return "#d9972b";
  return "#2fbf9b";
}

function toEditableTerm(term: EffectiveTerm): EditableTerm {
  return {
    ...term,
    draftValue: term.normalized_value,
    draftUnit: term.unit,
  };
}

function fromEditableTerm(term: EditableTerm): EffectiveTerm {
  return {
    ...term,
    normalized_value: term.draftValue,
    unit: term.draftUnit,
  };
}

function hasReviewIssues(items: EffectiveTerm[]) {
  return items.some((term) => term.review_status === "requires_human_review" || term.ambiguous);
}

function updateDraft(
  id: number,
  key: "draftValue" | "draftUnit",
  value: string,
  setTerms: React.Dispatch<React.SetStateAction<EditableTerm[]>>,
) {
  setTerms((current) => current.map((term) => (term.id === id ? { ...term, [key]: value } : term)));
}

function humanize(value: string) {
  return value.replaceAll("_", " ");
}

function formatMoney(value: number, currency: string) {
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCompactMoney(value: number, currency: string) {
  if (currency === "INR") {
    const absolute = Math.abs(value);
    if (absolute >= 10000000) return `${value < 0 ? "-" : ""}₹${(absolute / 10000000).toFixed(1)}Cr`;
    if (absolute >= 100000) return `${value < 0 ? "-" : ""}₹${(absolute / 100000).toFixed(1)}L`;
  }

  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}
