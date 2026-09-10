import type { LatestObservation } from "@/lib/types";

export const SHELF_SELECT =
  "merchant_id,pincode,product_id,sku_name,brand_name,pack_raw,pack_ml,pack_g,selling_price,mrp,discount_percent,availability,shelf_position,organic_rank,is_sponsored,rating,rating_count,search_query,unit_price_per_l,unit_price_per_kg";

export function packLabel(row: LatestObservation): string {
  if (row.pack_raw) return row.pack_raw;
  if (row.pack_g) return `${row.pack_g} g`;
  if (row.pack_ml) return `${row.pack_ml} ml`;
  return "—";
}

export function unitPrice(row: LatestObservation): string {
  if (row.unit_price_per_kg != null) return `₹${row.unit_price_per_kg}/kg`;
  if (row.unit_price_per_l != null) return `₹${row.unit_price_per_l}/L`;
  return "—";
}

export function shelfRowKey(row: LatestObservation): string {
  return `${row.merchant_id ?? ""}-${row.pincode}-${row.product_id}-${row.search_query ?? ""}`;
}
