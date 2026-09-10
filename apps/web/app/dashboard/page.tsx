import Link from "next/link";
import { redirect } from "next/navigation";

import { SetupStepper } from "@/components/setup-stepper";
import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import type { Keyword, LatestObservation } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE = 50;

type Search = Promise<{
  pincode?: string;
  keyword?: string;
  availability?: string;
  from?: string;
}>;

function packLabel(row: LatestObservation): string {
  if (row.pack_raw) return row.pack_raw;
  if (row.pack_g) return `${row.pack_g} g`;
  if (row.pack_ml) return `${row.pack_ml} ml`;
  return "—";
}

function unitPrice(row: LatestObservation): string {
  if (row.unit_price_per_kg != null) return `₹${row.unit_price_per_kg}/kg`;
  if (row.unit_price_per_l != null) return `₹${row.unit_price_per_l}/L`;
  return "—";
}

function qs(params: { pincode?: string; keyword?: string; availability?: string; from?: number }): string {
  const sp = new URLSearchParams();
  if (params.pincode) sp.set("pincode", params.pincode);
  if (params.keyword) sp.set("keyword", params.keyword);
  if (params.availability) sp.set("availability", params.availability);
  if (params.from) sp.set("from", String(params.from));
  const s = sp.toString();
  return s ? `?${s}` : "";
}

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
  if (params.keyword) query = query.eq("search_query", params.keyword);

  const [{ data: observations, error: obsError }, { data: keywords, error: kwError }] = await Promise.all([
    query,
    supabase.from("keywords").select("id, query").eq("brand_id", brandId).order("query"),
  ]);

  const rows = (observations as LatestObservation[] | null) ?? [];
  const keywordList = (keywords as Pick<Keyword, "id" | "query">[] | null) ?? [];
  const schemaError = kwError?.message || obsError?.message;

  return (
    <div>
      <SetupStepper current="dashboard" />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl">Latest shelf</h1>
          <p className="mt-1 text-ink/70">
            Every product card from the last scrape of your selected keywords and stores. Two stores on the same pin
            stay as two rows (apply migration 0004 if they collapse).
          </p>
        </div>
        <Link href="/setup" className="rounded-full bg-ink px-4 py-2 text-sm text-lime">
          Run from Setup
        </Link>
      </div>
      {schemaError ? (
        <p className="mt-4 text-sm text-oos">
          {schemaError.includes("keywords")
            ? `Keywords table missing. Apply supabase/migrations/0003_keywords_locations_harvest.sql. ${schemaError}`
            : schemaError}
        </p>
      ) : null}
      {rows.length === 0 && !schemaError ? (
        <div className="mt-6 rounded-2xl border border-ink/10 bg-white/70 p-5 text-sm text-ink/70">
          <p>Nothing on the shelf yet. That is normal until a scrape finishes.</p>
          <ol className="mt-3 list-decimal space-y-1 pl-5">
            <li>
              Upload or add keywords and locations on{" "}
              <Link className="underline" href="/setup">
                Setup
              </Link>
              , then check the rows to scrape.
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
          name="keyword"
          defaultValue={params.keyword ?? ""}
          className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
        >
          <option value="">Any keyword</option>
          {keywordList.map((kw) => (
            <option key={kw.id} value={kw.query}>
              {kw.query}
            </option>
          ))}
        </select>
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
        <button type="submit" className="rounded-full bg-ink px-4 py-2 text-sm text-lime">
          Filter
        </button>
      </form>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Brand</th>
              <th className="px-3 py-2">Pack</th>
              <th className="px-3 py-2">MRP</th>
              <th className="px-3 py-2">Selling</th>
              <th className="px-3 py-2">Discount %</th>
              <th className="px-3 py-2">Sponsored</th>
              <th className="px-3 py-2">Rating</th>
              <th className="px-3 py-2">Reviews</th>
              <th className="px-3 py-2">Store</th>
              <th className="px-3 py-2">Pin</th>
              <th className="px-3 py-2">Keyword</th>
              <th className="px-3 py-2">Stock</th>
              <th className="px-3 py-2">Rank</th>
              <th className="px-3 py-2">₹/kg or ₹/L</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.merchant_id ?? ""}-${row.pincode}-${row.product_id}-${row.search_query ?? ""}`} className="border-t border-ink/5">
                <td className="px-3 py-2">{row.sku_name}</td>
                <td className="px-3 py-2">{row.brand_name ?? "—"}</td>
                <td className="px-3 py-2">{packLabel(row)}</td>
                <td className="px-3 py-2 tabular">{row.mrp ?? "—"}</td>
                <td className="px-3 py-2 tabular">{row.selling_price ?? "—"}</td>
                <td className="px-3 py-2 tabular">{row.discount_percent ?? "—"}</td>
                <td className="px-3 py-2">{row.is_sponsored ? "yes" : "—"}</td>
                <td className="px-3 py-2 tabular">{row.rating ?? "—"}</td>
                <td className="px-3 py-2 tabular">{row.rating_count ?? "—"}</td>
                <td className="px-3 py-2">{row.merchant_id ?? "—"}</td>
                <td className="px-3 py-2">
                  <Link className="underline" href={`/pins/${row.pincode}`}>
                    {row.pincode}
                  </Link>
                </td>
                <td className="px-3 py-2">{row.search_query || "—"}</td>
                <td className={`px-3 py-2 ${row.availability === "in_stock" ? "text-stock" : "text-oos"}`}>
                  {row.availability}
                </td>
                <td className="px-3 py-2 tabular">{row.shelf_position ?? row.organic_rank ?? "—"}</td>
                <td className="px-3 py-2 tabular">{unitPrice(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex gap-2">
        {from > 0 ? (
          <Link
            className="rounded-full border border-ink/20 px-3 py-1 text-sm"
            href={`/dashboard${qs({ pincode: params.pincode, keyword: params.keyword, availability: params.availability, from: Math.max(0, from - PAGE) })}`}
          >
            Previous
          </Link>
        ) : null}
        {rows.length === PAGE ? (
          <Link
            className="rounded-full border border-ink/20 px-3 py-1 text-sm"
            href={`/dashboard${qs({ pincode: params.pincode, keyword: params.keyword, availability: params.availability, from: from + PAGE })}`}
          >
            Next page
          </Link>
        ) : null}
      </div>
    </div>
  );
}
