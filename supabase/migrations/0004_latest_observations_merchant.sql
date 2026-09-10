-- Two merchants on the same pincode + product + query must remain two rows.
-- Apply only this file after 0003. Do not re-run 0001.

create or replace view latest_observations as
select distinct on (brand_id, merchant_id, pincode, product_id, search_query)
  *
from observations
order by brand_id, merchant_id, pincode, product_id, search_query, observed_slot desc;

alter view latest_observations set (security_invoker = true);

do $$
begin
  grant select on latest_observations to authenticated;
  grant select on latest_observations to service_role;
exception
  when undefined_object then
    null;
end $$;
