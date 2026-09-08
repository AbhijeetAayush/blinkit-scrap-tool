from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


SkuRole = Literal["self", "brand_competitor"]
SlotKind = Literal["morning", "evening", "resolve", "manual"]
Availability = Literal["in_stock", "oos", "delisted"]
MatchRelation = Literal["exact", "like_item", "unmatched"]


class CoveragePin(BaseModel):
    id: UUID
    brand_id: UUID
    pincode: str
    city: str | None = None
    locality: str | None = None
    lat: float
    lon: float
    tier: str = "hot"
    platform: str = "blinkit"
    active: bool = True


class Sku(BaseModel):
    id: UUID
    brand_id: UUID
    sku_role: SkuRole
    display_name: str
    search_query: str
    brand_name: str
    pack_raw: str | None = None
    pack_ml: int | None = None
    kvi_flag: bool = True
    blinkit_product_id: str | None = None
    active: bool = True


class StoreRef(BaseModel):
    platform: str
    merchant_id: str
    merchant_type: str | None = None
    serviceable: bool = True
    lat: float | None = None
    lon: float | None = None
    city_id: str | None = None


class ParsedListing(BaseModel):
    product_id: str
    variant_id: str | None = None
    group_id: str | None = None
    sku_name: str
    brand_name: str | None = None
    pack_raw: str | None = None
    mrp: float | None = None
    selling_price: float | None = None
    in_stock: bool = True
    inventory_shown: int | None = None
    qty_cap: int | None = None
    is_sponsored: bool | None = None
    shelf_position: int | None = None
    organic_rank: int | None = None
    rating: float | None = None
    rating_count: int | None = None
    image_url: str | None = None
    product_url: str | None = None
    offer_text: str | None = None
    discount_text: str | None = None
    delivery_promise_min: int | None = None
    delivery_time_text: str | None = None
    category_path: list[str] = Field(default_factory=list)
    search_query: str = ""


class FetchResult(BaseModel):
    html: str
    cookies: str | None = None
    status_code: int = 200
    vendor: str
    credits_hint: float | None = None


class ObservationDraft(BaseModel):
    brand_id: UUID | None = None
    run_id: UUID | None = None
    platform: str
    merchant_id: str
    pincode: str
    product_id: str
    variant_id: str | None = None
    group_id: str | None = None
    sku_name: str
    brand_name: str | None = None
    pack_raw: str | None = None
    pack_ml: int | None = None
    category_path: list[str] = Field(default_factory=list)
    product_url: str | None = None
    image_url: str | None = None
    mrp: float | None = None
    selling_price: float | None = None
    discount_percent: float | None = None
    discount_text: str | None = None
    offer_text: str | None = None
    currency: str = "INR"
    availability: Availability
    inventory_shown: int | None = None
    qty_cap: int | None = None
    low_stock_badge: bool = False
    shelf_position: int | None = None
    organic_rank: int | None = None
    is_sponsored: bool | None = None
    search_query: str | None = None
    result_page: int | None = 1
    delivery_promise_min: int | None = None
    delivery_time_text: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    sku_id: UUID | None = None
    sku_role: SkuRole | None = None
    match_confidence: float | None = None
    match_method: str | None = None
    unit_price_per_l: float | None = None
    unlocker_vendor: str | None = None
    observed_at: datetime
    observed_slot: datetime
    s3_bronze_key: str | None = None
    payload_hash: str | None = None


class DispatchPlan(BaseModel):
    run_id: UUID
    observed_slot: datetime
    stores: list[StoreRef] = Field(default_factory=list)
    continuation_offset: int | None = None


class ScrapeJob(BaseModel):
    brand_ids: list[UUID] = Field(default_factory=list)
    merchant_id: str
    platform: str
    run_id: UUID
    correlation_id: str
    observed_slot: datetime


class DeriveJob(BaseModel):
    run_id: UUID
    brand_id: UUID | None = None


class MatchResult(BaseModel):
    sku_id: UUID | None = None
    relation: MatchRelation
    confidence: float
    method: str
    sku_role: SkuRole | None = None


class DispatchPayload(BaseModel):
    continuation_offset: int = 0
    observed_slot: datetime | None = None
    run_id: UUID | None = None
    slot_kind: SlotKind = "morning"
    self_url: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
