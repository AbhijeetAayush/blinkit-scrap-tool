from __future__ import annotations

import uuid
from typing import Any

from src.app.clock import now_utc, observed_slot
from src.app.settings import Settings
from src.domain.errors import UnlockerBlockedError, UnserviceableError
from src.domain.models import CoveragePin, DispatchPayload, ScrapeJob, StoreRef
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

        remaining = self._credits.remaining()
        if remaining <= 0:
            self._alerts.insert(None, "credit_budget", {"remaining": remaining})
            return {"status": "budget", "remaining": remaining}

        run_id = payload.run_id or self._runs.create(
            kind="dispatch",
            brand_id=None,
            correlation_id=str(uuid.uuid4()),
            continuation_offset=payload.continuation_offset,
        )
        slot = payload.observed_slot or observed_slot(now_utc(), payload.slot_kind)

        pins = self._coverage.list_active_pins(
            offset=payload.continuation_offset,
            limit=self._settings.pin_page_size,
        )
        missing = self._store_map.missing_pins(pins)
        if missing and self._resolve is not None:
            try:
                self._resolve.run([str(p.id) for p in missing])
            except Exception:
                # Location unlocker flakiness must not block scrape publish.
                pass
        else:
            for batch in _chunks(missing, 20):
                self._publisher.publish_resolve({"pincode_ids": [str(p.id) for p in batch]})

        stores: dict[tuple[str, str], StoreRef] = {}
        brand_ids_by_store: dict[tuple[str, str], set] = {}
        for pin in pins:
            mapped = self._store_map.get(pin.platform, pin.pincode)
            if mapped is None or not mapped.serviceable:
                continue
            key = (mapped.platform, mapped.merchant_id)
            stores[key] = mapped
            brand_ids_by_store.setdefault(key, set()).add(pin.brand_id)

        published = 0
        continued = False
        for (platform, merchant_id), store in stores.items():
            if published >= self._settings.max_stores_per_dispatch:
                self._publisher.publish_dispatch_continuation(
                    offset=payload.continuation_offset + len(pins),
                    run_id=run_id,
                    observed_slot=slot,
                    slot_kind=payload.slot_kind,
                    self_url=payload.self_url or self._settings.dispatch_function_url,
                )
                continued = True
                break
            lock_key = f"lock:scrape:{platform}:{merchant_id}"
            if not self._lock.acquire(lock_key, 600):
                continue
            job = ScrapeJob(
                brand_ids=list(brand_ids_by_store.get((platform, merchant_id), [])),
                merchant_id=merchant_id,
                platform=platform,
                run_id=run_id,
                correlation_id=str(uuid.uuid4()),
                observed_slot=slot,
            )
            delay = published * self._settings.scrape_spread_seconds
            self._publisher.publish_scrape(job, delay)
            published += 1

        more = len(pins) == self._settings.pin_page_size
        if more and published < self._settings.max_stores_per_dispatch:
            self._publisher.publish_dispatch_continuation(
                offset=payload.continuation_offset + len(pins),
                run_id=run_id,
                observed_slot=slot,
                slot_kind=payload.slot_kind,
                self_url=payload.self_url or self._settings.dispatch_function_url,
            )
            continued = True

        if not continued:
            self._runs.finish(run_id, status="dispatched", pages_ok=published)

        return {
            "status": "ok",
            "run_id": str(run_id),
            "pins": len(pins),
            "published": published,
            "observed_slot": slot.isoformat(),
        }


def _chunks(items: list[CoveragePin], size: int) -> list[list[CoveragePin]]:
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
