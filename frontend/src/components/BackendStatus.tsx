"use client";

import { Activity, Database, Server } from "lucide-react";
import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "@/lib/api";

export function BackendStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

  const statusText = error ? "Offline" : health ? "Connected" : "Checking";

  return (
    <section className="border-b border-ink/10 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-steel">System status</p>
          <h2 className="text-xl font-semibold text-ink">Backend connection is {statusText.toLowerCase()}</h2>
        </div>
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div className="flex min-w-24 items-center gap-2 rounded-md border border-ink/10 px-3 py-2">
            <Activity size={16} />
            {statusText}
          </div>
          <div className="flex min-w-24 items-center gap-2 rounded-md border border-ink/10 px-3 py-2">
            <Server size={16} />
            {health?.service ?? "DealLab"}
          </div>
          <div className="flex min-w-24 items-center gap-2 rounded-md border border-ink/10 px-3 py-2">
            <Database size={16} />
            {health?.database ?? "Pending"}
          </div>
        </div>
      </div>
      {error ? <p className="mx-auto max-w-6xl px-6 pb-4 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}
