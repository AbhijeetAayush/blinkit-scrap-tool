import { redirect } from "next/navigation";

import { RunNowButton } from "@/components/run-now-button";
import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import type { RunRow } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const brandId = await currentBrandId();
  if (!brandId) redirect("/onboarding");
  const supabase = await createClient();
  const { data } = await supabase
    .from("runs")
    .select("id, brand_id, kind, started_at, finished_at, status, pages_ok, pages_fail, credits_hint, error")
    .eq("brand_id", brandId)
    .order("started_at", { ascending: false })
    .limit(80);

  const rows = (data as RunRow[] | null) ?? [];

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-moss">Dispatch</p>
          <h1 className="mt-1 font-display text-3xl tracking-tight">Runs</h1>
          <p className="mt-1 text-ink/70">Dispatch health. System runs may have a null brand_id.</p>
        </div>
        <RunNowButton brandId={brandId} />
      </div>
      <div className="table-wrap mt-6">
        <table className="data-table">
          <thead>
            <tr>
              <th>Kind</th>
              <th>Status</th>
              <th>Started</th>
              <th>Finished</th>
              <th>Pages</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.kind}</td>
                <td>
                  <span className={row.status === "derived" ? "badge badge-stock" : "badge"}>{row.status}</span>
                </td>
                <td>{new Date(row.started_at).toLocaleString("en-IN")}</td>
                <td>{row.finished_at ? new Date(row.finished_at).toLocaleString("en-IN") : "—"}</td>
                <td className="tabular">
                  {row.pages_ok}/{row.pages_fail}
                </td>
                <td className="text-oos">{row.error ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
