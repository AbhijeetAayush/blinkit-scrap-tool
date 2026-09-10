import Link from "next/link";
import { redirect } from "next/navigation";

import { ShelfTable } from "@/components/shelf-table";
import { SetupStepper } from "@/components/setup-stepper";
import { currentBrandId } from "@/lib/brand";
import { SHELF_SELECT } from "@/lib/shelf";
import { createClient } from "@/lib/supabase/server";
import type { LatestObservation } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE = 50;

type Search = Promise<{
  pincode?: string;
  keyword?: string;
  availability?: string;
  from?: string;
}>;

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
    .select(SHELF_SELECT)
    .eq("brand_id", brandId)
    .order("observed_slot", { ascending: false })
    .range(from, from + PAGE - 1);

  if (params.pincode) query = query.eq("pincode", params.pincode);
  if (params.availability) query = query.eq("availability", params.availability);
  if (params.keyword) query = query.eq("search_query", params.keyword.trim());

  const { data: observations, error: obsError } = await query;
  const rows = (observations as LatestObservation[] | null) ?? [];
  const schemaError = obsError?.message;

  return (
    <div>
      <SetupStepper current="dashboard" />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-moss">Shelf</p>
          <h1 className="mt-1 font-display text-3xl tracking-tight">Latest harvest</h1>
          <p className="mt-1 max-w-2xl text-ink/70">
            Every product card from the last scrape. Two stores on the same pin stay as two rows.
          </p>
        </div>
        <Link href="/setup" prefetch className="btn">
          Run from Setup
        </Link>
      </div>
      {schemaError ? (
        <p className="mt-4 text-sm text-oos">
          {schemaError.includes("keywords") || schemaError.includes("latest_observations")
            ? `Apply supabase/migrations/0003 then 0004. ${schemaError}`
            : schemaError}
        </p>
      ) : null}
      {rows.length === 0 && !schemaError ? (
        <div className="card mt-6 p-5 text-sm text-ink/70">
          <p>Nothing on the shelf yet. That is normal until a scrape finishes.</p>
          <ol className="mt-3 list-decimal space-y-1 pl-5">
            <li>
              Check keywords and locations on{" "}
              <Link className="link" href="/setup">
                Setup
              </Link>
              , then run.
            </li>
            <li>Wait until Working… stops.</li>
            <li>Refresh this page.</li>
          </ol>
        </div>
      ) : null}

      <form className="mt-6 flex flex-wrap gap-2" method="get">
        <input name="pincode" defaultValue={params.pincode ?? ""} placeholder="Pincode" className="field" />
        <input
          name="keyword"
          defaultValue={params.keyword ?? ""}
          placeholder="Keyword query"
          className="field min-w-[12rem]"
        />
        <select name="availability" defaultValue={params.availability ?? ""} className="field">
          <option value="">Any availability</option>
          <option value="in_stock">in stock</option>
          <option value="oos">oos</option>
          <option value="delisted">delisted</option>
        </select>
        <button type="submit" className="btn">
          Filter
        </button>
      </form>

      <div className="mt-5">
        <ShelfTable rows={rows} showPin />
      </div>
      <div className="mt-4 flex gap-2">
        {from > 0 ? (
          <Link
            prefetch
            className="btn-ghost"
            href={`/dashboard${qs({ pincode: params.pincode, keyword: params.keyword, availability: params.availability, from: Math.max(0, from - PAGE) })}`}
          >
            Previous
          </Link>
        ) : null}
        {rows.length === PAGE ? (
          <Link
            prefetch
            className="btn-ghost"
            href={`/dashboard${qs({ pincode: params.pincode, keyword: params.keyword, availability: params.availability, from: from + PAGE })}`}
          >
            Next page
          </Link>
        ) : null}
      </div>
    </div>
  );
}
