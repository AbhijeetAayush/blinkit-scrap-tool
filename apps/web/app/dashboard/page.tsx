import Link from "next/link";
import { redirect } from "next/navigation";

import { RunNowButton } from "@/components/run-now-button";
import { SetupStepper } from "@/components/setup-stepper";
import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import type { LatestObservation, Sku } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE = 50;

type Search = Promise<{
  pincode?: string;
  availability?: string;
  sku?: string;
  from?: string;
}>;

export default async function DashboardPage({ searchParams }: { searchParams: Search }) {
  const brandId = await currentBrandId();
  if (!brandId) redirect("/onboarding");
  const params = await searchParams;
  const from = Number(params.from ?? "0") || 0;

  const supabase = await createClient();
  let query = supabase
    .from("latest_observations")
    .select("*")
    .eq("brand_id", brandId)
    .order("observed_slot", { ascending: false })
    .range(from, from + PAGE - 1);

  if (params.pincode) query = query.eq("pincode", params.pincode);
  if (params.availability) query = query.eq("availability", params.availability);
  if (params.sku) query = query.eq("sku_id", params.sku);

  const [{ data: observations }, { data: skus }] = await Promise.all([
    query,
    supabase.from("skus").select("id, display_name").eq("brand_id", brandId),
  ]);

  const rows = (observations as LatestObservation[] | null) ?? [];
  const skuList = (skus as Pick<Sku, "id" | "display_name">[] | null) ?? [];
  const skuName = Object.fromEntries(skuList.map((s) => [s.id, s.display_name]));

  return (
    <div>
      <SetupStepper current="dashboard" />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Latest shelf</h1>
          <p className="mt-1 text-ink/70">Price, stock, and rank from the last successful scrape.</p>
        </div>
        <RunNowButton />
      </div>
      {rows.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-ink/10 bg-white/70 p-5 text-sm text-ink/70">
          <p>Nothing on the shelf yet. That is normal until a scrape finishes.</p>
          <ol className="mt-3 list-decimal space-y-1 pl-5">
            <li>
              Finish SKUs + pincode on{" "}
              <Link className="underline" href="/setup">
                Setup
              </Link>
              .
            </li>
            <li>Click Run scrape and wait about a minute.</li>
            <li>Refresh this page. Rows appear after the scrape Lambda finishes.</li>
          </ol>
        </div>
      ) : null}

      <form className="mt-6 flex flex-wrap gap-2" method="get">
        <input
          name="pincode"
          defaultValue={params.pincode ?? ""}
          placeholder="Pincode"
          className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
        />
        <select
          name="availability"
          defaultValue={params.availability ?? ""}
          className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
        >
          <option value="">Any availability</option>
          <option value="in_stock">in_stock</option>
          <option value="oos">oos</option>
          <option value="delisted">delisted</option>
        </select>
        <select name="sku" defaultValue={params.sku ?? ""} className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
          <option value="">Any SKU</option>
          {skuList.map((sku) => (
            <option key={sku.id} value={sku.id}>
              {sku.display_name}
            </option>
          ))}
        </select>
        <button type="submit" className="rounded-full bg-ink px-4 py-2 text-sm text-lime">
          Filter
        </button>
      </form>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">SKU</th>
              <th className="px-3 py-2">Pin</th>
              <th className="px-3 py-2">Price</th>
              <th className="px-3 py-2">₹/L</th>
              <th className="px-3 py-2">Stock</th>
              <th className="px-3 py-2">Rank</th>
              <th className="px-3 py-2">Ad</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.pincode}-${row.product_id}`} className="border-t border-ink/5">
                <td className="px-3 py-2">{skuName[row.sku_id ?? ""] ?? row.sku_name}</td>
                <td className="px-3 py-2">
                  <Link className="underline" href={`/pins/${row.pincode}`}>
                    {row.pincode}
                  </Link>
                </td>
                <td className="px-3 py-2 tabular">{row.selling_price ?? "—"}</td>
                <td className="px-3 py-2 tabular">{row.unit_price_per_l ?? "—"}</td>
                <td className={`px-3 py-2 ${row.availability === "in_stock" ? "text-stock" : "text-oos"}`}>
                  {row.availability}
                </td>
                <td className="px-3 py-2 tabular">{row.shelf_position ?? row.organic_rank ?? "—"}</td>
                <td className="px-3 py-2">{row.is_sponsored ? "yes" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex gap-2">
        {from > 0 ? (
          <Link
            className="rounded-full border border-ink/20 px-3 py-1 text-sm"
            href={`/dashboard?from=${Math.max(0, from - PAGE)}`}
          >
            Previous
          </Link>
        ) : null}
        {rows.length === PAGE ? (
          <Link className="rounded-full border border-ink/20 px-3 py-1 text-sm" href={`/dashboard?from=${from + PAGE}`}>
            Next page
          </Link>
        ) : null}
      </div>
    </div>
  );
}
