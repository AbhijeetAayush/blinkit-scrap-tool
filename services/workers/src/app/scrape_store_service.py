from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from src.app.settings import Settings
from src.domain.errors import ParseEmptyError, UnlockerBlockedError
from src.domain.models import DeriveJob, ObservationDraft, ScrapeJob
from src.domain.ports import (
    AlertRepo,
    CoverageRepo,
    CreditMeter,
    JobPublisher,
    Lake,
    Lock,
    ObservationRepo,
    PlatformRegistry,
    ReviewQueueRepo,
    StoreMapRepo,
    UnlockerRouter,
)
from src.normalize.pack import parse_pack
from src.normalize.unit_price import discount_percent, unit_price_per_kg, unit_price_per_l


class ScrapeStoreService:
    def __init__(
        self,
        settings: Settings,
        coverage: CoverageRepo,
        store_map: StoreMapRepo,
        observations: ObservationRepo,
        alerts: AlertRepo,
        publisher: JobPublisher,
        lock: Lock,
        credits: CreditMeter,
        lake: Lake,
        platforms: PlatformRegistry,
        router: UnlockerRouter,
        review: ReviewQueueRepo | None = None,
    ) -> None:
        self._settings = settings
        self._coverage = coverage
        self._store_map = store_map
        self._observations = observations
        self._alerts = alerts
        self._publisher = publisher
        self._lock = lock
        self._credits = credits
        self._lake = lake
        self._platforms = platforms
        self._router = router
        self._review = review

    def run(self, job: ScrapeJob) -> dict[str, Any]:
        if self._lock.is_halted(str(job.run_id)) and self._settings.fail_fast:
            return {"status": "halted"}

        lock_key = f"lock:scrape:{job.platform}:{job.merchant_id}:{job.correlation_id}"
        try:
            if not self._lock.acquire(lock_key, 600):
                return {"status": "locked"}
            return self._run_unlocked(job)
        finally:
            self._lock.release(lock_key)

    def _tenant_brand(self, job: ScrapeJob):
        if job.brand_id:
            return job.brand_id
        return job.brand_ids[0] if job.brand_ids else None

    def _run_unlocked(self, job: ScrapeJob) -> dict[str, Any]:
        queries = [q.strip() for q in (job.queries or []) if q and q.strip()]
        catalog = self._platforms.get(job.platform)
        unlocker, vendor = self._router.session_for_store(job.merchant_id)
        tenant = self._tenant_brand(job)
        lat = job.lat
        lon = job.lon
        pin = job.pincode or "unknown"
        drafts: list[ObservationDraft] = []
        now = datetime.now(timezone.utc)
        pages_fail = 0

        for query in queries:
            listings = None
            try:
                listings = catalog.search(unlocker, None, query, lat=lat, lon=lon)
            except ParseEmptyError as exc:
                html = getattr(exc, "html", "") or ""
                if html:
                    bronze_key = (
                        f"bronze/platform={job.platform}/dt={now.date().isoformat()}/"
                        f"hour={now.hour:02d}/store={job.merchant_id}/{job.correlation_id}-empty.html"
                    )
                    self._lake.put_bronze(bronze_key, html.encode()[:1_500_000])
                if "ProductSkeleton" in html:
                    try:
                        listings = catalog.search(unlocker, None, query, lat=lat, lon=lon)
                    except ParseEmptyError as retry_exc:
                        retry_html = getattr(retry_exc, "html", "") or ""
                        if retry_html:
                            bronze_key = (
                                f"bronze/platform={job.platform}/dt={now.date().isoformat()}/"
                                f"hour={now.hour:02d}/store={job.merchant_id}/"
                                f"{job.correlation_id}-empty-retry.html"
                            )
                            self._lake.put_bronze(bronze_key, retry_html.encode()[:1_500_000])
                        self._alerts.insert(
                            tenant,
                            "parse_empty",
                            {
                                "merchant_id": job.merchant_id,
                                "query": query,
                                "reason": "skeleton",
                                "vendor": vendor,
                            },
                        )
                        pages_fail += 1
                        continue
                    except UnlockerBlockedError:
                        listings = None
                else:
                    self._alerts.insert(
                        tenant,
                        "parse_empty",
                        {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                    )
                    pages_fail += 1
                    continue
            except UnlockerBlockedError:
                listings = None

            if listings is None:
                if self._settings.unlocker_failover:
                    unlocker, vendor = self._router.failover_session(job.merchant_id)
                    try:
                        listings = catalog.search(unlocker, None, query, lat=lat, lon=lon)
                    except ParseEmptyError as exc:
                        html = getattr(exc, "html", "") or ""
                        if html:
                            bronze_key = (
                                f"bronze/platform={job.platform}/dt={now.date().isoformat()}/"
                                f"hour={now.hour:02d}/store={job.merchant_id}/{job.correlation_id}-empty.html"
                            )
                            self._lake.put_bronze(bronze_key, html.encode()[:1_500_000])
                        self._alerts.insert(
                            tenant,
                            "parse_empty",
                            {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                        )
                        pages_fail += 1
                        continue
                    except Exception:
                        self._alerts.insert(
                            tenant,
                            "unlocker_fail",
                            {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                        )
                        pages_fail += 1
                        continue
                else:
                    self._alerts.insert(
                        tenant,
                        "unlocker_fail",
                        {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                    )
                    pages_fail += 1
                    continue

            raw = json.dumps([lst.model_dump(mode="json") for lst in listings]).encode()
            if len(raw) > 1_500_000:
                raw = raw[:1_500_000]
            bronze_key = (
                f"bronze/platform={job.platform}/dt={now.date().isoformat()}/"
                f"hour={now.hour:02d}/store={job.merchant_id}/"
                f"{job.correlation_id}-{hashlib.sha1(query.encode()).hexdigest()[:10]}.json"
            )
            self._lake.put_bronze(bronze_key, raw)
            hint = getattr(unlocker, "last_credits_hint", None)
            self._credits.add(float(hint) if hint else 5.0)

            for listing in listings:
                pack = parse_pack(listing.pack_raw)
                availability = "in_stock" if listing.in_stock else "oos"
                off = discount_percent(listing.mrp, listing.selling_price, listing.discount_percent)
                payload_hash = hashlib.sha256(
                    f"{listing.product_id}:{listing.selling_price}:{availability}:{query}".encode()
                ).hexdigest()
                drafts.append(
                    ObservationDraft(
                        brand_id=tenant,
                        run_id=job.run_id,
                        platform=job.platform,
                        merchant_id=job.merchant_id,
                        pincode=pin,
                        product_id=listing.product_id,
                        variant_id=listing.variant_id,
                        group_id=listing.group_id,
                        sku_name=listing.sku_name,
                        brand_name=listing.brand_name,
                        pack_raw=listing.pack_raw,
                        pack_ml=pack.pack_ml,
                        pack_g=pack.pack_g,
                        category_path=listing.category_path,
                        product_url=listing.product_url,
                        image_url=listing.image_url,
                        mrp=listing.mrp,
                        selling_price=listing.selling_price,
                        discount_percent=off,
                        offer_text=listing.offer_text,
                        discount_text=listing.discount_text,
                        availability=availability,
                        inventory_shown=listing.inventory_shown,
                        qty_cap=listing.qty_cap,
                        shelf_position=listing.shelf_position,
                        organic_rank=listing.organic_rank,
                        is_sponsored=listing.is_sponsored,
                        search_query=query,
                        delivery_promise_min=listing.delivery_promise_min,
                        delivery_time_text=listing.delivery_time_text,
                        rating=listing.rating,
                        rating_count=listing.rating_count,
                        sku_id=None,
                        sku_role=None,
                        unit_price_per_l=unit_price_per_l(listing.selling_price, pack.pack_ml),
                        unit_price_per_kg=unit_price_per_kg(listing.selling_price, pack.pack_g),
                        unlocker_vendor=vendor,
                        observed_at=now,
                        observed_slot=job.observed_slot,
                        s3_bronze_key=bronze_key,
                        payload_hash=payload_hash,
                    )
                )

        self._observations.upsert_many(drafts)
        self._publisher.publish_derive(DeriveJob(run_id=job.run_id))
        return {
            "status": "ok",
            "rows": len(drafts),
            "queries": len(queries),
            "pages_fail": pages_fail,
        }
