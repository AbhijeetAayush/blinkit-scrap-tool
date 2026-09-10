import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { ShelfTable } from "@/components/shelf-table";
import { currentBrandId } from "@/lib/brand";
import { SHELF_SELECT } from "@/lib/shelf";
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
    .select(SHELF_SELECT)
    .eq("brand_id", brandId)
    .eq("pincode", pincode)
    .order("shelf_position", { ascending: true })
    .limit(500);

  const rows = (data as LatestObservation[] | null) ?? [];

  return (
    <div>
      <Link href="/dashboard" prefetch className="link text-sm">
        ← Shelf
      </Link>
      <h1 className="mt-3 font-display text-3xl tracking-tight">Pin {pincode}</h1>
      <p className="mt-1 text-ink/70">
        Latest harvest for this pincode, by store. Two merchants on the same pin are two rows.
      </p>
      <div className="mt-6">
        <ShelfTable rows={rows} />
      </div>
    </div>
  );
}
