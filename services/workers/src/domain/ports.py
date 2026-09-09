from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.domain.models import (
    CoveragePin,
    DeriveJob,
    FetchResult,
    Keyword,
    ObservationDraft,
    ParsedListing,
    ScrapeJob,
    Sku,
    StoreRef,
)


class Unlocker(Protocol):
    vendor: str

    def fetch(
        self,
        url: str,
        *,
        render: bool = False,
        country: str = "in",
        wait_for: str | None = None,
        cookies: str | None = None,
        js_scenario: dict | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult: ...


class UnlockerRouter(Protocol):
    def session_for_store(self, store_id: str) -> tuple[Unlocker, str]: ...

    def failover_session(self, store_id: str) -> tuple[Unlocker, str]: ...


class PlatformCatalog(Protocol):
    platform_id: str

    def resolve_store(self, lat: float, lon: float, unlocker: Unlocker) -> StoreRef: ...

    def search(
        self,
        unlocker: Unlocker,
        cookies: str | None,
        query: str,
        lat: float | None = None,
        lon: float | None = None,
    ) -> list[ParsedListing]: ...


class CoverageRepo(Protocol):
    def list_active_pins(self, *, offset: int, limit: int) -> list[CoveragePin]: ...

    def list_active_skus_for_merchant(self, platform: str, merchant_id: str) -> list[Sku]: ...

    def list_active_skus(self, brand_id: UUID) -> list[Sku]: ...

    def get_pins_by_ids(self, pincode_ids: list[UUID]) -> list[CoveragePin]: ...

    def list_keywords_by_ids(self, keyword_ids: list[UUID]) -> list[Keyword]: ...

    def brand_ids_for_merchant(self, platform: str, merchant_id: str) -> list[UUID]: ...


class StoreMapRepo(Protocol):
    def get(self, platform: str, pincode: str) -> StoreRef | None: ...

    def upsert(self, pin: CoveragePin, store: StoreRef) -> None: ...

    def pins_for_merchant(self, platform: str, merchant_id: str) -> list[str]: ...

    def missing_pins(self, pins: list[CoveragePin]) -> list[CoveragePin]: ...


class ObservationRepo(Protocol):
    def upsert_many(self, drafts: list[ObservationDraft]) -> None: ...

    def list_for_run(self, run_id: UUID) -> list[dict[str, Any]]: ...

    def latest_product_ids(
        self, platform: str, merchant_id: str, search_query: str
    ) -> set[str]: ...

    def get_previous(
        self,
        platform: str,
        merchant_id: str,
        product_id: str,
        before_slot: datetime,
    ) -> dict[str, Any] | None: ...


class RunRepo(Protocol):
    def create(
        self,
        *,
        kind: str,
        brand_id: UUID | None,
        correlation_id: str | None,
        continuation_offset: int | None,
    ) -> UUID: ...

    def finish(
        self,
        run_id: UUID,
        *,
        status: str,
        pages_ok: int = 0,
        pages_fail: int = 0,
        credits_hint: float | None = None,
        error: str | None = None,
    ) -> None: ...


class AlertRepo(Protocol):
    def insert(self, brand_id: UUID | None, alert_type: str, payload: dict[str, Any]) -> None: ...


class MatchRepo(Protocol):
    def insert(
        self,
        observation_id: int,
        sku_id: UUID | None,
        relation: str,
        confidence: float,
        method: str,
        decided_by: str,
    ) -> None: ...


class OosRepo(Protocol):
    def open_window(
        self,
        brand_id: UUID,
        sku_id: UUID,
        merchant_id: str,
        started_at: datetime,
        velocity_source: str,
    ) -> None: ...

    def close_open_window(
        self,
        sku_id: UUID,
        merchant_id: str,
        ended_at: datetime,
        psl_inr: float | None,
    ) -> None: ...

    def list_open(self) -> list[dict[str, Any]]: ...


class SkuVelocityRepo(Protocol):
    def get(self, sku_id: UUID) -> tuple[float, str] | None: ...


class ReviewQueueRepo(Protocol):
    def insert_review(self, brand_id: UUID, payload: dict[str, Any]) -> None: ...


class JobPublisher(Protocol):
    def publish_scrape(self, job: ScrapeJob, delay_s: int) -> None: ...

    def publish_derive(self, job: DeriveJob) -> None: ...

    def publish_resolve(self, payload: dict[str, Any]) -> None: ...

    def publish_dispatch_continuation(
        self,
        offset: int,
        run_id: UUID,
        observed_slot: datetime,
        slot_kind: str,
        self_url: str,
        *,
        brand_id: UUID | None = None,
        keyword_ids: list[UUID] | None = None,
        pincode_ids: list[UUID] | None = None,
    ) -> None: ...


class Lock(Protocol):
    def acquire(self, key: str, ttl_s: int) -> bool: ...

    def release(self, key: str) -> None: ...

    def set_halt(self, run_id: str, ttl_s: int = 3600) -> None: ...

    def is_halted(self, run_id: str) -> bool: ...

    def cache_store(self, platform: str, pincode: str, payload: str, ttl_s: int = 86400) -> None: ...


class CreditMeter(Protocol):
    def add(self, n: float) -> None: ...

    def remaining(self) -> float: ...


class Lake(Protocol):
    def put_bronze(self, key: str, body: bytes) -> None: ...

    def put_silver(self, key: str, body: bytes) -> None: ...


class PlatformRegistry(Protocol):
    def get(self, platform: str) -> PlatformCatalog: ...
