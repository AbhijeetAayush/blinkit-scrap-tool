import { notFound, redirect } from "next/navigation";

import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import type { LatestObservation } from "@/lib/types";

export const dynamic = "force-dynamic";

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
      <p className="mt-1 text-ink/70">Latest listings for this catchment, same merchant facts cloned per mapped pin.</p>
      <div className="mt-6 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Product</th>
              <th className="px-3 py-2">Brand</th>
              <th className="px-3 py-2">Price</th>
              <th className="px-3 py-2">Stock</th>
              <th className="px-3 py-2">Rank</th>
              <th className="px-3 py-2">Inventory shown</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.product_id} className="border-t border-ink/5">
                <td className="px-3 py-2">{row.sku_name}</td>
                <td className="px-3 py-2">{row.brand_name}</td>
                <td className="px-3 py-2 tabular">{row.selling_price ?? "—"}</td>
                <td className={`px-3 py-2 ${row.availability === "in_stock" ? "text-stock" : "text-oos"}`}>
                  {row.availability}
                </td>
                <td className="px-3 py-2 tabular">{row.shelf_position ?? "—"}</td>
                <td className="px-3 py-2 tabular">{row.inventory_shown ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
