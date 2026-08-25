import { ShieldCheck, SlidersHorizontal, Upload } from "lucide-react";

import { BackendStatus } from "@/components/BackendStatus";
import { DealAnalyzer } from "@/components/DealAnalyzer";

const capabilities = [
  {
    icon: Upload,
    title: "Ingest contracts",
    body: "Accept text and PDF contracts, normalize the source, and preserve evidence for review.",
  },
  {
    icon: SlidersHorizontal,
    title: "Simulate economics",
    body: "Keep revenue, cost, margin, and exposure math inside deterministic backend services.",
  },
  {
    icon: ShieldCheck,
    title: "Approve changes",
    body: "Recommend safer structures while leaving final commercial action with a human owner.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-paper">
      <header className="border-b border-ink/10 bg-ink text-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 px-6 py-10">
          <p className="text-sm font-semibold uppercase tracking-wide text-mint">DealLab</p>
          <div className="max-w-3xl">
            <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
              AI deal engineering for enterprise contracts
            </h1>
            <p className="mt-4 text-base leading-7 text-white/78">
              Evaluate proposed commercial terms before signature, stress-test downside scenarios,
              and surface the smallest practical changes needed to protect margin.
            </p>
          </div>
        </div>
      </header>

      <BackendStatus />

      <section className="mx-auto grid max-w-6xl gap-4 px-6 py-8 md:grid-cols-3">
        {capabilities.map((item) => (
          <article key={item.title} className="rounded-md border border-ink/10 bg-white p-5">
            <item.icon className="mb-4 text-mint" size={24} />
            <h2 className="text-lg font-semibold text-ink">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-steel">{item.body}</p>
          </article>
        ))}
      </section>

      <DealAnalyzer />
    </main>
  );
}
