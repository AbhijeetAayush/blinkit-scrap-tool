from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShelfRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    run_id: UUID
    platform: str
    merchant_id: str
    pincode: str
    product_id: str
    variant_id: str | None = None
    group_id: str | None = None
    search_query: str
    sku_name: str
    brand_name: str | None = None
    pack_raw: str | None = None
    pack_ml: int | None = None
    pack_g: int | None = None
    mrp: float | None = None
    selling_price: float | None = None
    discount_percent: float | None = None
    discount_text: str | None = None
    offer_text: str | None = None
    currency: str = "INR"
    availability: str
    inventory_shown: int | None = None
    qty_cap: int | None = None
    low_stock_badge: bool = False
    shelf_position: int | None = None
    organic_rank: int | None = None
    is_sponsored: bool | None = None
    image_url: str | None = None
    product_url: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    delivery_promise_min: int | None = None
    delivery_time_text: str | None = None
    unit_price_per_kg: float | None = None
    unit_price_per_l: float | None = None
    category_path: list[str] = Field(default_factory=list)
    result_page: int | None = 1
    observed_at: datetime | None = None


class ShelfListResponse(BaseModel):
    items: list[ShelfRow]
    limit: int | None = None
