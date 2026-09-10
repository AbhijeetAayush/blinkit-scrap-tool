from __future__ import annotations

import uuid
from typing import Any

from src.app.clock import now_utc, observed_slot
from src.app.settings import Settings
from src.domain.errors import UnlockerBlockedError, UnserviceableError
from src.domain.models import CoveragePin, DispatchPayload, ScrapeJob, StoreRef
from src.normalize.keyword import normalize_keyword
from src.domain.ports import (
    AlertRepo,
    CoverageRepo,
    CreditMeter,
    JobPublisher,
    Lock,
    PlatformRegistry,
    RunRepo,
    StoreMapRepo,
)

QUERIES_PER_JOB = 6
CREDITS_PER_SEARCH = 5.0


class DispatchService:
    def __init__(
        self,
        settings: Settings,
        coverage: CoverageRepo,
        store_map: StoreMapRepo,
        runs: RunRepo,
        alerts: AlertRepo,
        publisher: JobPublisher,
        lock: Lock,
        credits: CreditMeter,
        platforms: PlatformRegistry,
        resolve: ResolveStoresService | None = None,
    ) -> None:
        self._settings = settings
        self._coverage = coverage
        self._store_map = store_map
        self._runs = runs
        self._alerts = alerts
        self._publisher = publisher
        self._lock = lock
        self._credits = credits
        self._platforms = platforms
        self._resolve = resolve

    def run(self, payload: DispatchPayload) -> dict[str, Any]:
        if payload.run_id and self._lock.is_halted(str(payload.run_id)) and self._settings.fail_fast:
            return {"status": "halted", "run_id": str(payload.run_id)}

        brand_id = payload.brand_id
        keyword_ids = list(payload.keyword_ids or [])
        pincode_ids = list(payload.pincode_ids or [])
        if not brand_id or not keyword_ids or not pincode_ids:
            return {"status": "error", "error": "brand_id, keyword_ids, and pincode_ids are required"}

        keywords = [
            k
            for k in self._coverage.list_keywords_by_ids(keyword_ids)
            if k.brand_id == brand_id and k.active and k.query
        ]
        all_pins = [
            p
            for p in self._coverage.get_pins_by_ids(pincode_ids)
            if p.brand_id == brand_id and p.active
        ]
        queries = list(dict.fromkeys(q for k in keywords if (q := normalize_keyword(k.query))))
        if not queries or not all_pins:
            return {"status": "error", "error": "no active keywords or locations for brand"}

        offset = payload.continuation_offset
        loc_page = all_pins[offset : offset + self._settings.max_stores_per_dispatch]
        pages = len(queries) * len(loc_page)
        needed = pages * CREDITS_PER_SEARCH
        remaining = self._credits.remaining()
        if remaining < needed:
            self._alerts.insert(brand_id, "credit_budget", {"remaining": remaining, "needed": needed, "pages": pages})
            if payload.run_id:
                self._runs.finish(
                    payload.run_id,
                    status="budget",
                    error="daily search budget",
                )
            return {"status": "budget", "remaining": remaining, "needed": needed, "pages": pages}

        run_id = payload.run_id or self._runs.create(
            kind="dispatch",
            brand_id=brand_id,
            correlation_id=str(uuid.uuid4()),
            continuation_offset=payload.continuation_offset,
        )
        slot = payload.observed_slot or observed_slot(now_utc(), payload.slot_kind)
        if offset == 0:
            chunks_per = max(1, (len(queries) + QUERIES_PER_JOB - 1) // QUERIES_PER_JOB)
            setter = getattr(self._lock, "set_jobs_left", None)
            if callable(setter):
                setter(str(run_id), chunks_per * len(all_pins))

        published = 0
        job_count = 0
        for pin in loc_page:
            merchant_id = f"geo:{pin.lat:.4f},{pin.lon:.4f}"
            for chunk in _chunks(queries, QUERIES_PER_JOB):
                job = ScrapeJob(
                    brand_ids=[brand_id],
                    brand_id=brand_id,
                    merchant_id=merchant_id,
                    platform=pin.platform or "blinkit",
                    run_id=run_id,
                    correlation_id=str(uuid.uuid4()),
                    observed_slot=slot,
                    queries=chunk,
                    pincode=pin.pincode,
                    lat=pin.lat,
                    lon=pin.lon,
                )
                delay = job_count * self._settings.scrape_spread_seconds
                self._publisher.publish_scrape(job, delay)
                job_count += 1
            published += 1

        next_offset = offset + len(loc_page)
        if next_offset < len(all_pins):
            self._publisher.publish_dispatch_continuation(
                offset=next_offset,
                run_id=run_id,
                observed_slot=slot,
                slot_kind=payload.slot_kind,
                self_url=payload.self_url or self._settings.dispatch_function_url,
                brand_id=brand_id,
                keyword_ids=keyword_ids,
                pincode_ids=pincode_ids,
            )

        return {
            "status": "ok",
            "run_id": str(run_id),
            "pins": len(loc_page),
            "published": job_count,
            "locations": published,
            "queries": len(queries),
            "observed_slot": slot.isoformat(),
        }


def _chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class ResolveStoresService:
    def __init__(
        self,
        coverage: CoverageRepo,
        store_map: StoreMapRepo,
        platforms: PlatformRegistry,
        lock: Lock,
        location_unlocker,
    ) -> None:
        self._coverage = coverage
        self._store_map = store_map
        self._platforms = platforms
        self._lock = lock
        self._unlocker = location_unlocker

    def run(self, pincode_ids: list[str]) -> dict[str, Any]:
        if pincode_ids:
            pins = self._coverage.get_pins_by_ids([uuid.UUID(i) for i in pincode_ids])
        else:
            pins = []
            offset = 0
            page_size = 500
            while True:
                page = self._coverage.list_active_pins(offset=offset, limit=page_size)
                if not page:
                    break
                pins.extend(self._store_map.missing_pins(page))
                if len(page) < page_size:
                    break
                offset += page_size
        ok = 0
        for pin in pins:
            catalog = self._platforms.get(pin.platform)
            try:
                store = catalog.resolve_store(pin.lat, pin.lon, self._unlocker)
            except UnserviceableError:
                store = StoreRef(
                    platform=pin.platform,
                    merchant_id=f"unserviceable:{pin.pincode}",
                    serviceable=False,
                    lat=pin.lat,
                    lon=pin.lon,
                )
            except UnlockerBlockedError:
                store = StoreRef(
                    platform=pin.platform,
                    merchant_id=f"geo:{pin.lat:.4f},{pin.lon:.4f}",
                    serviceable=True,
                    lat=pin.lat,
                    lon=pin.lon,
                )
            self._store_map.upsert(pin, store)
            self._lock.cache_store(pin.platform, pin.pincode, store.model_dump_json())
            ok += 1
        return {"resolved": ok}
