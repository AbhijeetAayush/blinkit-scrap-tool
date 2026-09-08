-- OPTIONAL DEMO DATA ONLY.
-- Workers never import this file. Production tenants start empty and add
-- SKUs / pincodes in the UI. Delete or skip this file for a blank project.

insert into brands (id, name, home_city)
values ('00000000-0000-0000-0000-000000000001', 'Demo Dairy', 'Bengaluru')
on conflict (id) do nothing;

insert into skus (brand_id, sku_role, display_name, search_query, brand_name, pack_raw, pack_ml)
values
  ('00000000-0000-0000-0000-000000000001', 'self', 'Demo Gold Milk 500ml', 'toned milk 500', 'DemoGold', '500 ml', 500),
  ('00000000-0000-0000-0000-000000000001', 'brand_competitor', 'Rival A Milk 500ml', 'toned milk 500', 'RivalA', '500 ml', 500),
  ('00000000-0000-0000-0000-000000000001', 'brand_competitor', 'Rival B Milk 500ml', 'toned milk 500', 'RivalB', '500 ml', 500);

insert into pincodes (brand_id, platform, pincode, city, locality, lat, lon, tier)
values
  ('00000000-0000-0000-0000-000000000001', 'blinkit', '000001', 'DemoCity', 'Area One', 12.9352, 77.6245, 'hot'),
  ('00000000-0000-0000-0000-000000000001', 'blinkit', '000002', 'DemoCity', 'Area Two', 12.9121, 77.6446, 'hot'),
  ('00000000-0000-0000-0000-000000000001', 'blinkit', '000003', 'DemoCity', 'Area Three', 12.9698, 77.7500, 'hot');
