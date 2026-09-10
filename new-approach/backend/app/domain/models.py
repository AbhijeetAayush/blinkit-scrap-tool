from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"
    cancelled = "cancelled"


class RunJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Listing(BaseModel):
    product_id: str
    variant_id: str | None = None
    group_id: str | None = None
    sku_name: str
    brand_name: str | None = None
    pack_raw: str | None = None
    mrp: float | None = None
    selling_price: float | None = None
    discount_percent: float | None = None
    discount_text: str | None = None
    offer_text: str | None = None
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
    delivery_promise_min: int | None = None
    delivery_time_text: str | None = None
    category_path: list[str] = Field(default_factory=list)
    search_query: str = ""
    result_page: int | None = 1


class ScrapeJob(BaseModel):
    run_id: UUID
    run_job_id: UUID
    workspace_id: UUID
    platform: str
    location_id: UUID
    pincode: str
    lat: float
    lon: float
    queries: list[str] = Field(min_length=1)


def geo_merchant(lat: float, lon: float) -> str:
    return f"geo:{lat:.4f},{lon:.4f}"


def chunk_queries(queries: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise ValueError("chunk size must be >= 1")
    return [queries[i : i + size] for i in range(0, len(queries), size)]


def utcnow() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)
