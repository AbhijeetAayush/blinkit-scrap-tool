-- Expand observations to match harvest fields from the prior Blinkit pipeline.
ALTER TABLE observations
  ADD COLUMN IF NOT EXISTS variant_id text,
  ADD COLUMN IF NOT EXISTS group_id text,
  ADD COLUMN IF NOT EXISTS discount_text text,
  ADD COLUMN IF NOT EXISTS offer_text text,
  ADD COLUMN IF NOT EXISTS pack_ml int,
  ADD COLUMN IF NOT EXISTS pack_g int,
  ADD COLUMN IF NOT EXISTS unit_price_per_kg numeric,
  ADD COLUMN IF NOT EXISTS unit_price_per_l numeric,
  ADD COLUMN IF NOT EXISTS delivery_promise_min int,
  ADD COLUMN IF NOT EXISTS inventory_shown int,
  ADD COLUMN IF NOT EXISTS qty_cap int,
  ADD COLUMN IF NOT EXISTS low_stock_badge boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS currency text NOT NULL DEFAULT 'INR',
  ADD COLUMN IF NOT EXISTS category_path text[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS result_page int DEFAULT 1;

-- Align OOS token with prior harvest (oos vs out_of_stock).
UPDATE observations
SET availability = 'oos'
WHERE availability IN ('out_of_stock', 'oos', 'delisted')
  AND availability <> 'in_stock';
