CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext NOT NULL UNIQUE,
  password_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspace_members (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('owner', 'member')),
  PRIMARY KEY (user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS keywords (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  query text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, query)
);

CREATE TABLE IF NOT EXISTS locations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  platform text NOT NULL DEFAULT 'blinkit',
  pincode text NOT NULL,
  store_name text,
  lat double precision NOT NULL,
  lon double precision NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, platform, lat, lon)
);

CREATE TABLE IF NOT EXISTS runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('queued', 'running', 'done', 'error', 'cancelled')),
  pages_ok int NOT NULL DEFAULT 0,
  pages_fail int NOT NULL DEFAULT 0,
  jobs_total int NOT NULL DEFAULT 0,
  jobs_done int NOT NULL DEFAULT 0,
  error text,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS run_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  platform text NOT NULL,
  location_id uuid NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  queries jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'running', 'done', 'failed')),
  error text,
  attempts int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS observations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  platform text NOT NULL,
  merchant_id text NOT NULL,
  pincode text NOT NULL,
  product_id text NOT NULL,
  variant_id text,
  group_id text,
  search_query text NOT NULL DEFAULT '',
  sku_name text NOT NULL,
  brand_name text,
  pack_raw text,
  pack_ml int,
  pack_g int,
  mrp numeric,
  selling_price numeric,
  discount_percent numeric,
  discount_text text,
  offer_text text,
  currency text NOT NULL DEFAULT 'INR',
  availability text NOT NULL DEFAULT 'in_stock',
  inventory_shown int,
  qty_cap int,
  low_stock_badge boolean NOT NULL DEFAULT false,
  shelf_position int,
  organic_rank int,
  is_sponsored boolean,
  image_url text,
  product_url text,
  rating numeric,
  rating_count int,
  delivery_promise_min int,
  delivery_time_text text,
  unit_price_per_kg numeric,
  unit_price_per_l numeric,
  category_path text[] NOT NULL DEFAULT '{}',
  result_page int DEFAULT 1,
  observed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (platform, merchant_id, pincode, product_id, search_query, run_id)
);

CREATE INDEX IF NOT EXISTS observations_workspace_observed_idx
  ON observations (workspace_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS observations_workspace_platform_pin_idx
  ON observations (workspace_id, platform, pincode);
CREATE INDEX IF NOT EXISTS observations_run_idx ON observations (run_id);
CREATE INDEX IF NOT EXISTS run_jobs_run_idx ON run_jobs (run_id);

CREATE OR REPLACE VIEW latest_observations AS
SELECT DISTINCT ON (workspace_id, platform, merchant_id, pincode, product_id, search_query)
  *
FROM observations
ORDER BY workspace_id, platform, merchant_id, pincode, product_id, search_query, observed_at DESC;
