"use client";

import { BarChart3, FileText, Loader2, Send } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useState } from "react";

import { analyzeContractText, type ContractAnalysisResponse } from "@/lib/api";

const sampleContract = `Customer: Acme Corp.
ACV $500,000.
Contract term 24 months.
Discount 30%.
Variable cost 42%.
Support cost $80,000.
Payment terms Net 90.
Usage commitment $200,000.
Liability cap 2x.`;

export function DealAnalyzer() {
  const [text, setText] = useState(sampleContract);
  const [analysis, setAnalysis] = useState<ContractAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function submit() {
    setIsLoading(true);
    setError(null);

    try {
      const result = await analyzeContractText(text, "draft-contract.txt");
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setIsLoading(false);
    }
  }

  const terms = analysis?.analysis.terms;
  const scenarios = analysis?.analysis.scenarios ?? [];

  return (
    <section className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="rounded-md border border-ink/10 bg-white p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-steel">Contract input</p>
            <h2 className="text-xl font-semibold text-ink">Analyze proposed terms</h2>
          </div>
          <FileText className="text-mint" size={24} />
        </div>
        <textarea
          className="min-h-72 w-full resize-y rounded-md border border-ink/15 bg-paper p-3 text-sm leading-6 outline-none focus:border-mint"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button
          className="mt-4 inline-flex items-center gap-2 rounded-md bg-mint px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
          onClick={submit}
          disabled={isLoading || text.trim().length < 20}
        >
          {isLoading ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
          Run analysis
        </button>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      </div>

      <div className="rounded-md border border-ink/10 bg-white p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-steel">Deal economics</p>
            <h2 className="text-xl font-semibold text-ink">
              {analysis ? `Health score ${analysis.analysis.health_score}` : "Awaiting analysis"}
            </h2>
          </div>
          <BarChart3 className="text-amber" size={24} />
        </div>

        {analysis ? (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <Metric label="ACV" value={`$${terms?.annual_contract_value.toLocaleString()}`} />
              <Metric label="Discount" value={`${terms?.discount_percent}%`} />
              <Metric label="Payment" value={`Net ${terms?.payment_terms_days}`} />
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scenarios}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="scenario_name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="gross_margin_percent" name="Gross margin %" fill="#2fbf9b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="downside_exposure" name="Exposure" fill="#d9972b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <InsightList title="Fragile terms" items={analysis.analysis.fragile_terms} />
              <InsightList title="Recommended changes" items={analysis.analysis.recommendations} />
            </div>
          </div>
        ) : (
          <div className="flex min-h-72 items-center justify-center rounded-md border border-dashed border-ink/15 bg-paper text-sm text-steel">
            Submit contract text to receive deterministic scenario economics.
          </div>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-md border border-ink/10 bg-paper p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-steel">{label}</p>
      <p className="mt-1 text-lg font-semibold text-ink">{value}</p>
    </div>
  );
}

function InsightList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold uppercase tracking-wide text-steel">{title}</h3>
      <ul className="mt-2 space-y-2 text-sm leading-6 text-ink">
        {items.map((item) => (
          <li key={item} className="rounded-md bg-paper px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
