export type SkuRole = "self" | "brand_competitor";
export type Availability = "in_stock" | "oos" | "delisted";
export type PinTier = "hot" | "warm" | "cold";

export type Brand = {
  id: string;
  name: string;
  logo_url: string | null;
  home_city: string | null;
};

export type Sku = {
  id: string;
  brand_id: string;
  sku_role: SkuRole;
  display_name: string;
  search_query: string;
  brand_name: string;
  pack_raw: string | null;
  pack_ml: number | null;
  pack_g: number | null;
  kvi_flag: boolean;
  blinkit_product_id: string | null;
  active: boolean;
};

export type Keyword = {
  id: string;
  brand_id: string;
  query: string;
  active: boolean;
};

export type CoveragePin = {
  id: string;
  brand_id: string;
  platform: string;
  pincode: string;
  city: string | null;
  locality: string | null;
  store_name: string | null;
  lat: number;
  lon: number;
  tier: PinTier;
  active: boolean;
};

export type LatestObservation = {
  brand_id: string | null;
  pincode: string;
  product_id: string;
  sku_name: string;
  brand_name: string | null;
  pack_raw: string | null;
  pack_ml: number | null;
  pack_g: number | null;
  selling_price: number | null;
  mrp: number | null;
  discount_percent: number | null;
  discount_text: string | null;
  availability: Availability;
  inventory_shown: number | null;
  shelf_position: number | null;
  organic_rank: number | null;
  is_sponsored: boolean | null;
  rating: number | null;
  rating_count: number | null;
  sku_id: string | null;
  sku_role: SkuRole | null;
  search_query: string | null;
  unit_price_per_l: number | null;
  unit_price_per_kg: number | null;
  observed_slot: string;
  platform: string;
};

export type AlertRow = {
  id: string;
  brand_id: string | null;
  type: string;
  payload: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
};

export type RunRow = {
  id: string;
  brand_id: string | null;
  kind: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  pages_ok: number;
  pages_fail: number;
  credits_hint: number | null;
  error: string | null;
};
