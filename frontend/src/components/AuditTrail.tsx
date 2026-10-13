"use client";

import { History, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { getDealAudit, type AuditEvent } from "@/lib/api";

export function AuditTrail({ dealId }: { dealId: number }) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDealAudit(dealId).then(setEvents).finally(() => setLoading(false));
  }, [dealId]);

  return (
    <details className="mt-6 rounded-md border border-ink/10 bg-white p-4">
      <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold uppercase tracking-wide text-steel"><History size={16} /> Audit history</summary>
      {loading ? <Loader2 className="mt-3 animate-spin text-steel" size={16} /> : <ul className="mt-3 space-y-2 text-sm">{events.map((event) => <li key={event.id} className="border-t border-ink/10 pt-2"><span className="font-semibold text-ink">{event.action.replaceAll("_", " ")}</span><span className="ml-2 text-xs text-steel">{event.created_at}</span></li>)}</ul>}
    </details>
  );
}
