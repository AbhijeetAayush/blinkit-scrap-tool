# Shared types

`observation.schema.json` matches the Python `ObservationDraft` model used when writing S3 silver/bronze payloads and Postgres `observations` rows.

Workers serialize drafts with Pydantic `model_dump(mode="json")`. The unique observation key is `(platform, merchant_id, product_id, observed_slot)`.
