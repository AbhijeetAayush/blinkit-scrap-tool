import { notFound, redirect } from "next/navigation";

import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import type { LatestObservation } from "@/lib/types";

export const dynamic = "force-dynamic";

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

export default async function PinDetailPage({ params }: { params: Promise<{ pincode: string }> }) {
  const brandId = await currentBrandId();
  if (!brandId) redirect("/onboarding");
  const { pincode } = await params;
  if (!pincode) notFound();

  const supabase = await createClient();
  const { data } = await supabase
    .from("latest_observations")
    .select("*")
    .eq("brand_id", brandId)
    .eq("pincode", pincode)
    .order("shelf_position", { ascending: true });

  const rows = (data as LatestObservation[] | null) ?? [];

  return (
    <div>
      <h1 className="font-display text-3xl">Pin {pincode}</h1>
      <p className="mt-1 text-ink/70">
        Latest harvest for this pincode, by store. Two merchants on the same pin are two rows, not a cloned pin.
      </p>
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
              <th className="px-3 py-2">Keyword</th>
              <th className="px-3 py-2">Stock</th>
              <th className="px-3 py-2">Rank</th>
              <th className="px-3 py-2">₹/kg or ₹/L</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.merchant_id ?? ""}-${row.product_id}-${row.search_query ?? ""}`} className="border-t border-ink/5">
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
                <td className="px-3 py-2">{row.search_query || "—"}</td>
                <td className={`px-3 py-2 ${row.availability === "in_stock" ? "text-stock" : "text-oos"}`}>
                  {row.availability}
                </td>
                <td className="px-3 py-2 tabular">{row.shelf_position ?? "—"}</td>
                <td className="px-3 py-2 tabular">{unitPrice(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
