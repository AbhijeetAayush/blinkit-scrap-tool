import { redirect } from "next/navigation";

import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import type { AlertRow } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function AlertsPage() {
  const brandId = await currentBrandId();
  if (!brandId) redirect("/onboarding");
  const supabase = await createClient();
  const { data } = await supabase
    .from("alerts")
    .select("*")
    .eq("brand_id", brandId)
    .order("created_at", { ascending: false })
    .limit(200);

  const rows = (data as AlertRow[] | null) ?? [];

  return (
    <div>
      <h1 className="font-display text-3xl">Alerts</h1>
      <p className="mt-1 text-ink/70">OOS, rival cheaper, parse empty, unlocker fail, credit budget.</p>
      <ul className="mt-6 space-y-3">
        {rows.map((row) => (
          <li key={row.id} className="rounded-2xl border border-ink/10 bg-white/70 p-4">
            <div className="flex items-center justify-between gap-4">
              <span className="font-semibold">{row.type}</span>
              <span className="text-xs text-ink/50">{new Date(row.created_at).toLocaleString("en-IN")}</span>
            </div>
            <pre className="mt-2 overflow-x-auto text-xs text-ink/70">{JSON.stringify(row.payload, null, 2)}</pre>
          </li>
        ))}
        {rows.length === 0 ? <li className="text-ink/50">No alerts yet.</li> : null}
      </ul>
    </div>
  );
}
