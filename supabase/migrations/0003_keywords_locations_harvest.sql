-- Keyword harvest: store-level locations, harvest observations, no SKU gate.
-- Apply in Supabase SQL editor. Do not re-run 0001.

create table if not exists keywords (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  query text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (brand_id, query)
);

create index if not exists keywords_brand_query_idx on keywords (brand_id, query);

alter table pincodes add column if not exists store_name text;

alter table pincodes drop constraint if exists pincodes_brand_id_platform_pincode_key;
alter table pincodes drop constraint if exists pincodes_brand_platform_lat_lon_key;
drop index if exists pincodes_brand_platform_lat_lon_uidx;
alter table pincodes
  add constraint pincodes_brand_platform_lat_lon_key unique (brand_id, platform, lat, lon);

alter table observations add column if not exists pack_g int;
alter table observations add column if not exists unit_price_per_kg numeric;

update observations set search_query = '' where search_query is null;
alter table observations alter column search_query set default '';
alter table observations alter column search_query set not null;

alter table observations drop constraint if exists observations_slot_pin_product_uidx;
alter table observations drop constraint if exists observations_platform_merchant_id_pincode_product_id_observed_slot_key;
alter table observations
  add constraint observations_slot_pin_product_query_uidx
  unique (platform, merchant_id, pincode, product_id, search_query, observed_slot);

create or replace view latest_observations as
select distinct on (brand_id, pincode, product_id, search_query)
  *
from observations
order by brand_id, pincode, product_id, search_query, observed_slot desc;

alter view latest_observations set (security_invoker = true);

alter table keywords enable row level security;

drop policy if exists member_access on keywords;
create policy member_access on keywords
  for all using (brand_id in (select public.user_brand_ids()))
  with check (brand_id in (select public.user_brand_ids()));

do $$
begin
  grant select, insert, update, delete on keywords to authenticated;
  grant select, insert, update, delete on keywords to service_role;
  grant select on latest_observations to authenticated;
  grant select on latest_observations to service_role;
exception
  when undefined_object then
    null;
end $$;
