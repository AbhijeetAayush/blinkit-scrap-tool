-- SELECT * views freeze columns at create time; recreate after observation field expansions.
CREATE OR REPLACE VIEW latest_observations AS
SELECT DISTINCT ON (workspace_id, platform, merchant_id, pincode, product_id, search_query)
  *
FROM observations
ORDER BY workspace_id, platform, merchant_id, pincode, product_id, search_query, observed_at DESC;
