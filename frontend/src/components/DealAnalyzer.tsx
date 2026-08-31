"use client";

import { FileText, Loader2, Save, Send, Upload } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";

import {
  analyzeDeal,
  evaluateEconomics,
  updateEffectiveTerm,
  type CompanyAssumptions,
  type DealIntelligenceResponse,
  type EconomicScenarioInput,
  type EffectiveTerm,
  type ReviewStatus,
  type ScenarioEconomicsResult,
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
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);

  const unresolvedCount = useMemo(
    () => terms.filter((term) => term.review_status === "requires_human_review" || term.ambiguous).length,
    [terms],
  );

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
                  className="mt-4 inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  onClick={calculateEconomics}
                  disabled={isEvaluating}
                >
                  {isEvaluating ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Calculate Economics
                </button>
              </div>
            </div>

            {economics ? <EconomicsResult result={economics} /> : null}
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
