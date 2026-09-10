from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Listing, utcnow
from app.infrastructure.db.models import Observation
from app.normalize.pack import parse_pack
from app.normalize.unit_price import discount_percent, unit_price_per_kg, unit_price_per_l


class ObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(
        self,
        *,
        workspace_id: UUID,
        run_id: UUID,
        platform: str,
        merchant_id: str,
        pincode: str,
        listings: list[Listing],
    ) -> int:
        if not listings:
            return 0
        now = utcnow()
        rows: list[dict[str, Any]] = []
        for listing in listings:
            pack = parse_pack(listing.pack_raw)
            off = discount_percent(listing.mrp, listing.selling_price, listing.discount_percent)
            rows.append(
                {
                    "workspace_id": workspace_id,
                    "run_id": run_id,
                    "platform": platform,
                    "merchant_id": merchant_id,
                    "pincode": pincode,
                    "product_id": listing.product_id,
                    "variant_id": listing.variant_id,
                    "group_id": listing.group_id,
                    "search_query": listing.search_query or "",
                    "sku_name": listing.sku_name,
                    "brand_name": listing.brand_name,
                    "pack_raw": listing.pack_raw,
                    "pack_ml": pack.pack_ml,
                    "pack_g": pack.pack_g,
                    "mrp": listing.mrp,
                    "selling_price": listing.selling_price,
                    "discount_percent": off,
                    "discount_text": listing.discount_text,
                    "offer_text": listing.offer_text,
                    "currency": "INR",
                    "availability": "in_stock" if listing.in_stock else "oos",
                    "inventory_shown": listing.inventory_shown,
                    "qty_cap": listing.qty_cap,
                    "low_stock_badge": False,
                    "shelf_position": listing.shelf_position,
                    "organic_rank": listing.organic_rank,
                    "is_sponsored": listing.is_sponsored,
                    "image_url": listing.image_url,
                    "product_url": listing.product_url,
                    "rating": listing.rating,
                    "rating_count": listing.rating_count,
                    "delivery_promise_min": listing.delivery_promise_min,
                    "delivery_time_text": listing.delivery_time_text,
                    "unit_price_per_kg": unit_price_per_kg(listing.selling_price, pack.pack_g),
                    "unit_price_per_l": unit_price_per_l(listing.selling_price, pack.pack_ml),
                    "category_path": listing.category_path or [],
                    "result_page": listing.result_page or 1,
                    "observed_at": now,
                }
            )

        stmt = insert(Observation).values(rows)
        update_cols = {
            "variant_id": stmt.excluded.variant_id,
            "group_id": stmt.excluded.group_id,
            "sku_name": stmt.excluded.sku_name,
            "brand_name": stmt.excluded.brand_name,
            "pack_raw": stmt.excluded.pack_raw,
            "pack_ml": stmt.excluded.pack_ml,
            "pack_g": stmt.excluded.pack_g,
            "mrp": stmt.excluded.mrp,
            "selling_price": stmt.excluded.selling_price,
            "discount_percent": stmt.excluded.discount_percent,
            "discount_text": stmt.excluded.discount_text,
            "offer_text": stmt.excluded.offer_text,
            "availability": stmt.excluded.availability,
            "inventory_shown": stmt.excluded.inventory_shown,
            "qty_cap": stmt.excluded.qty_cap,
            "shelf_position": stmt.excluded.shelf_position,
            "organic_rank": stmt.excluded.organic_rank,
            "is_sponsored": stmt.excluded.is_sponsored,
            "image_url": stmt.excluded.image_url,
            "product_url": stmt.excluded.product_url,
            "rating": stmt.excluded.rating,
            "rating_count": stmt.excluded.rating_count,
            "delivery_promise_min": stmt.excluded.delivery_promise_min,
            "delivery_time_text": stmt.excluded.delivery_time_text,
            "unit_price_per_kg": stmt.excluded.unit_price_per_kg,
            "unit_price_per_l": stmt.excluded.unit_price_per_l,
            "category_path": stmt.excluded.category_path,
            "result_page": stmt.excluded.result_page,
            "observed_at": stmt.excluded.observed_at,
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "platform",
                "merchant_id",
                "pincode",
                "product_id",
                "search_query",
                "run_id",
            ],
            set_=update_cols,
        )
        await self._session.execute(stmt)
        return len(rows)

    async def list_latest(
        self,
        workspace_id: UUID,
        *,
        platform: str | None = None,
        pincode: str | None = None,
        q: str | None = None,
        merchant_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = ["workspace_id = :workspace_id"]
        params: dict[str, Any] = {"workspace_id": workspace_id, "limit": limit}
        if platform:
            clauses.append("platform = :platform")
            params["platform"] = platform
        if pincode:
            clauses.append("pincode = :pincode")
            params["pincode"] = pincode
        if merchant_id:
            clauses.append("merchant_id = :merchant_id")
            params["merchant_id"] = merchant_id
        if q:
            clauses.append("(search_query ILIKE :q OR sku_name ILIKE :q)")
            params["q"] = f"%{q}%"
        sql = (
            "SELECT * FROM latest_observations WHERE "
            + " AND ".join(clauses)
            + " ORDER BY observed_at DESC LIMIT :limit"
        )
        result = await self._session.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]
