export type User = {
  id: string;
  email: string;
  created_at: string | null;
};

export type Workspace = {
  id: string;
  name: string;
  created_at: string | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
  workspace: Workspace;
};

export type MeResponse = {
  user: User;
  workspace: Workspace;
};

export type Keyword = {
  id: string;
  workspace_id: string;
  query: string;
  active: boolean;
  created_at: string | null;
};

export type Location = {
  id: string;
  workspace_id: string;
  platform: string;
  pincode: string;
  store_name: string | null;
  lat: number;
  lon: number;
  active: boolean;
  created_at: string | null;
};

export type RunStatus = "queued" | "running" | "done" | "error" | "cancelled";
export type RunJobStatus = "pending" | "running" | "done" | "failed";

export type RunJob = {
  id: string;
  location_id: string;
  platform: string;
  status: RunJobStatus | string;
  error: string | null;
  queries?: string[] | null;
};

export type Run = {
  id: string;
  workspace_id: string;
  status: RunStatus | string;
  pages_ok: number;
  pages_fail: number;
  jobs_total: number;
  jobs_done: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  jobs?: RunJob[] | null;
};

export type CreateRunBody = {
  keyword_ids: string[];
  location_ids: string[];
};

export type ShelfRow = {
  id: string;
  workspace_id: string;
  run_id: string;
  platform: string;
  merchant_id: string;
  pincode: string;
  product_id: string;
  variant_id?: string | null;
  group_id?: string | null;
  search_query: string;
  sku_name: string;
  brand_name: string | null;
  pack_raw: string | null;
  pack_ml?: number | null;
  pack_g?: number | null;
  mrp: number | null;
  selling_price: number | null;
  discount_percent: number | null;
  discount_text?: string | null;
  offer_text?: string | null;
  currency?: string;
  availability: string;
  inventory_shown?: number | null;
  qty_cap?: number | null;
  low_stock_badge?: boolean;
  shelf_position: number | null;
  organic_rank: number | null;
  is_sponsored: boolean | null;
  image_url: string | null;
  product_url: string | null;
  rating: number | null;
  rating_count: number | null;
  delivery_promise_min?: number | null;
  delivery_time_text: string | null;
  unit_price_per_kg?: number | null;
  unit_price_per_l?: number | null;
  category_path?: string[];
  result_page?: number | null;
  observed_at: string | null;
};

export type ItemsResponse<T> = {
  items: T[];
};

export type ShelfListResponse = ItemsResponse<ShelfRow> & {
  limit?: number;
};
