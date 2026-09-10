import type { ShelfRow } from "@/lib/types";

export function packLabel(row: ShelfRow): string {
  if (row.pack_raw) return row.pack_raw;
  if (row.pack_g) return `${row.pack_g} g`;
  if (row.pack_ml) return `${row.pack_ml} ml`;
  return "—";
}

export function unitPrice(row: ShelfRow): string {
  if (row.unit_price_per_kg != null) return `₹${row.unit_price_per_kg}/kg`;
  if (row.unit_price_per_l != null) return `₹${row.unit_price_per_l}/L`;
  return "—";
}

export function shelfRowKey(row: ShelfRow): string {
  return `${row.merchant_id ?? ""}-${row.pincode}-${row.product_id}-${row.search_query ?? ""}-${row.id}`;
}
