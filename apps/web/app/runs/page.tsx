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
  const { data } = await supabase.from("runs").select("*").order("started_at", { ascending: false }).limit(100);
  const rows = (data as RunRow[] | null) ?? [];

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Runs</h1>
          <p className="mt-1 text-ink/70">Dispatch health. System runs may have a null brand_id.</p>
        </div>
        <RunNowButton />
      </div>
      <div className="mt-6 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Started</th>
              <th className="px-3 py-2">Finished</th>
              <th className="px-3 py-2">Pages</th>
              <th className="px-3 py-2">Error</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-ink/5">
                <td className="px-3 py-2">{row.kind}</td>
                <td className="px-3 py-2">{row.status}</td>
                <td className="px-3 py-2">{new Date(row.started_at).toLocaleString("en-IN")}</td>
                <td className="px-3 py-2">
                  {row.finished_at ? new Date(row.finished_at).toLocaleString("en-IN") : "—"}
                </td>
                <td className="px-3 py-2 tabular">
                  {row.pages_ok}/{row.pages_fail}
                </td>
                <td className="px-3 py-2 text-oos">{row.error ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
