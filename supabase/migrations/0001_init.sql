-- Brand shelf intelligence schema.
-- Coverage is unbounded: pincodes and skus are rows, not constants.

create extension if not exists pgcrypto;

create table if not exists brands (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  logo_url text,
  home_city text,
  created_at timestamptz not null default now()
);

create table if not exists brand_members (
  user_id uuid not null,
  brand_id uuid not null references brands(id) on delete cascade,
  role text not null check (role in ('owner', 'member')),
  primary key (user_id, brand_id)
);

create table if not exists skus (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  sku_role text not null check (sku_role in ('self', 'brand_competitor')),
  display_name text not null,
  search_query text not null,
  brand_name text not null,
  pack_raw text,
  pack_ml int,
  pack_g int,
  category_path text[],
  kvi_flag boolean not null default true,
  blinkit_product_id text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists pincodes (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid not null references brands(id) on delete cascade,
  platform text not null default 'blinkit',
  pincode text not null,
  city text,
  locality text,
  lat double precision not null,
  lon double precision not null,
  tier text not null default 'hot' check (tier in ('hot', 'warm', 'cold')),
  active boolean not null default true,
  unique (brand_id, platform, pincode)
);

create table if not exists store_map (
  platform text not null,
  pincode text not null,
  merchant_id text not null,
  merchant_type text,
  city_id text,
  serviceable boolean not null default true,
  lat double precision,
  lon double precision,
  updated_at timestamptz not null default now(),
  primary key (platform, pincode)
);

create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete set null,
  kind text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  pages_ok int not null default 0,
  pages_fail int not null default 0,
  credits_hint numeric,
  error text,
  correlation_id text,
  continuation_offset int
);

create table if not exists observations (
  id bigint generated always as identity primary key,
  brand_id uuid references brands(id) on delete set null,
  run_id uuid references runs(id) on delete set null,
  platform text not null,
  merchant_id text not null,
  pincode text not null,
  product_id text not null,
  variant_id text,
  group_id text,
  sku_name text not null,
  brand_name text,
  pack_raw text,
  pack_ml int,
  category_path text[],
  product_url text,
  image_url text,
  mrp numeric,
  selling_price numeric,
  discount_percent numeric,
  discount_text text,
  offer_text text,
  currency text not null default 'INR',
  availability text not null check (availability in ('in_stock', 'oos', 'delisted')),
  inventory_shown int,
  qty_cap int,
  low_stock_badge boolean not null default false,
  shelf_position int,
  organic_rank int,
  is_sponsored boolean,
  search_query text,
  result_page int,
  delivery_promise_min int,
  delivery_time_text text,
  rating numeric,
  rating_count int,
  sku_id uuid references skus(id) on delete set null,
  sku_role text,
  match_confidence numeric,
  match_method text,
  unit_price_per_l numeric,
  unlocker_vendor text,
  observed_at timestamptz not null,
  observed_slot timestamptz not null,
  s3_bronze_key text,
  payload_hash text,
  constraint observations_slot_pin_product_uidx
    unique (platform, merchant_id, pincode, product_id, observed_slot)
);

create index if not exists observations_brand_observed_idx
  on observations (brand_id, observed_at desc);
create index if not exists observations_sku_merchant_idx
  on observations (sku_id, merchant_id, observed_at desc);
create index if not exists observations_run_idx on observations (run_id);
create index if not exists observations_store_slot_idx
  on observations (platform, merchant_id, observed_slot);

create table if not exists matches (
  id uuid primary key default gen_random_uuid(),
  observation_id bigint references observations(id) on delete cascade,
  sku_id uuid references skus(id) on delete set null,
  relation text,
  confidence numeric,
  method text,
  decided_by text,
  created_at timestamptz not null default now()
);

create table if not exists review_queue (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  payload jsonb not null default '{}',
  status text not null default 'open',
  created_at timestamptz not null default now()
);

create table if not exists oos_windows (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  sku_id uuid references skus(id) on delete cascade,
  merchant_id text not null,
  started_at timestamptz not null,
  ended_at timestamptz,
  duration_hours numeric,
  psl_inr numeric,
  velocity_source text
);

create table if not exists alerts (
  id uuid primary key default gen_random_uuid(),
  brand_id uuid references brands(id) on delete cascade,
  type text not null,
  payload jsonb not null default '{}',
  created_at timestamptz not null default now(),
  read_at timestamptz
);

create table if not exists sku_velocity (
  sku_id uuid primary key references skus(id) on delete cascade,
  units_per_store_day numeric not null default 5,
  source text
);

create or replace view latest_observations as
select distinct on (brand_id, pincode, product_id)
  *
from observations
order by brand_id, pincode, product_id, observed_slot desc;

alter view latest_observations set (security_invoker = true);

create unique index if not exists matches_observation_uidx on matches (observation_id);

create or replace function public.user_brand_ids()
returns setof uuid
language sql
stable
security definer
set search_path = public
as $$
  select brand_id from public.brand_members where user_id = auth.uid();
$$;

create or replace function public.onboard_brand(p_name text, p_home_city text default null)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  bid uuid;
begin
  if auth.uid() is null then
    raise exception 'not authenticated';
  end if;
  if exists (select 1 from public.brand_members where user_id = auth.uid()) then
    select brand_id into bid from public.brand_members where user_id = auth.uid() limit 1;
    return bid;
  end if;
  insert into public.brands (name, home_city) values (p_name, p_home_city) returning id into bid;
  insert into public.brand_members (user_id, brand_id, role) values (auth.uid(), bid, 'owner');
  return bid;
end;
$$;

revoke all on function public.user_brand_ids() from public;
revoke all on function public.onboard_brand(text, text) from public;
grant execute on function public.user_brand_ids() to authenticated;
grant execute on function public.onboard_brand(text, text) to authenticated;

alter table brands enable row level security;
alter table brand_members enable row level security;
alter table skus enable row level security;
alter table pincodes enable row level security;
alter table store_map enable row level security;
alter table observations enable row level security;
alter table matches enable row level security;
alter table review_queue enable row level security;
alter table oos_windows enable row level security;
alter table alerts enable row level security;
alter table sku_velocity enable row level security;
alter table runs enable row level security;

create policy member_access on brands
  for all using (id in (select public.user_brand_ids()))
  with check (id in (select public.user_brand_ids()));

create policy brands_authenticated_insert on brands
  for insert with check (auth.uid() is not null);

create policy member_access on brand_members
  for all using (user_id = auth.uid() or brand_id in (select public.user_brand_ids()))
  with check (user_id = auth.uid());

create policy brand_members_self_insert on brand_members
  for insert with check (user_id = auth.uid());

create policy member_access on skus
  for all using (brand_id in (select public.user_brand_ids()))
  with check (brand_id in (select public.user_brand_ids()));

create policy member_access on pincodes
  for all using (brand_id in (select public.user_brand_ids()))
  with check (brand_id in (select public.user_brand_ids()));

create policy member_access on observations
  for all using (brand_id in (select public.user_brand_ids()))
  with check (brand_id in (select public.user_brand_ids()) or brand_id is null);

create policy member_access on matches
  for all using (
    sku_id in (select id from skus where brand_id in (select public.user_brand_ids()))
  );

create policy member_access on review_queue
  for all using (brand_id in (select public.user_brand_ids()));

create policy member_access on oos_windows
  for all using (brand_id in (select public.user_brand_ids()));

create policy member_access on alerts
  for all using (brand_id in (select public.user_brand_ids()));

create policy member_access on sku_velocity
  for all using (
    sku_id in (select id from skus where brand_id in (select public.user_brand_ids()))
  );

create policy member_access on runs
  for all using (
    brand_id is null
    or brand_id in (select public.user_brand_ids())
  );

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and tablename = 'observations'
  ) then
    alter publication supabase_realtime add table observations;
  end if;
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and tablename = 'alerts'
  ) then
    alter publication supabase_realtime add table alerts;
  end if;
exception
  when undefined_object then
    null;
end $$;

do $$
begin
  grant select on latest_observations to authenticated;
  grant select on latest_observations to service_role;
exception
  when undefined_object then
    null;
end $$;
