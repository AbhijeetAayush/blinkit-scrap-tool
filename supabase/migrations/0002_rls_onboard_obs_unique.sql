-- Fixes for databases that already applied 0001_init.sql.
-- Safe to re-run. Run this in the Supabase SQL editor if the project already exists.

alter table observations drop constraint if exists observations_platform_merchant_id_product_id_observed_slot_key;
alter table observations drop constraint if exists observations_platform_merchant_id_pincode_product_id_observed_slot_key;
alter table observations drop constraint if exists observations_slot_pin_product_uidx;
alter table observations
  add constraint observations_slot_pin_product_uidx
  unique (platform, merchant_id, pincode, product_id, observed_slot);

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

alter table store_map enable row level security;

drop policy if exists member_access on brands;
drop policy if exists member_access on brand_members;
drop policy if exists member_access on skus;
drop policy if exists member_access on pincodes;
drop policy if exists member_access on observations;
drop policy if exists member_access on matches;
drop policy if exists member_access on review_queue;
drop policy if exists member_access on oos_windows;
drop policy if exists member_access on alerts;
drop policy if exists member_access on sku_velocity;
drop policy if exists member_access on runs;

create policy member_access on brands
  for all using (id in (select public.user_brand_ids()))
  with check (id in (select public.user_brand_ids()));

create policy member_access on brand_members
  for all using (user_id = auth.uid() or brand_id in (select public.user_brand_ids()))
  with check (user_id = auth.uid());

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
