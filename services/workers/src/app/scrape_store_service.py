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
from src.match.cascade import listing_tracked, match_listing
from src.normalize.pack import parse_pack
from src.normalize.unit_price import unit_price_per_l


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

        lock_key = f"lock:scrape:{job.platform}:{job.merchant_id}"
        try:
            return self._run_unlocked(job)
        finally:
            self._lock.release(lock_key)

    def _tenant_brand(self, job: ScrapeJob, sku_brand=None):
        if sku_brand:
            return sku_brand
        return job.brand_ids[0] if job.brand_ids else None

    def _run_unlocked(self, job: ScrapeJob) -> dict[str, Any]:
        skus = self._coverage.list_active_skus_for_merchant(job.platform, job.merchant_id)
        queries = list(dict.fromkeys(s.search_query for s in skus if s.search_query))
        catalog = self._platforms.get(job.platform)
        unlocker, vendor = self._router.session_for_store(job.merchant_id)
        pins = self._store_map.pins_for_merchant(job.platform, job.merchant_id)
        tenant = self._tenant_brand(job)
        mapped = None
        lat = lon = None
        if pins:
            mapped = self._store_map.get(job.platform, pins[0])
            if mapped and mapped.lat is not None and mapped.lon is not None:
                lat, lon = float(mapped.lat), float(mapped.lon)
        drafts: list[ObservationDraft] = []
        now = datetime.now(timezone.utc)

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
                # Skeleton = render too early. Do NOT fail over to ZenRows (never gets cards).
                # One same-vendor retry; UnlockerBlockedError still may failover below.
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
                        continue
                    except UnlockerBlockedError:
                        listings = None
                else:
                    self._alerts.insert(
                        tenant,
                        "parse_empty",
                        {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                    )
                    if self._settings.fail_fast:
                        self._lock.set_halt(str(job.run_id))
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
                        continue
                    except Exception:
                        self._alerts.insert(
                            tenant,
                            "unlocker_fail",
                            {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                        )
                        continue
                else:
                    self._alerts.insert(
                        tenant,
                        "unlocker_fail",
                        {"merchant_id": job.merchant_id, "query": query, "vendor": vendor},
                    )
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
            self._credits.add(float(hint) if hint else 1.0)

            matched_product_ids: set[str] = set()
            for listing in listings:
                result = match_listing(listing, skus, auto_commit=self._settings.match_auto_commit)
                if not listing_tracked(listing, skus, result):
                    continue
                pack = parse_pack(listing.pack_raw)
                availability = "in_stock" if listing.in_stock else "oos"
                brand_id = result.sku_id and next((s.brand_id for s in skus if s.id == result.sku_id), None)
                if (
                    self._review
                    and brand_id
                    and result.sku_id
                    and 0.70 <= result.confidence < self._settings.match_auto_commit
                    and result.method != "product_id"
                ):
                    self._review.insert_review(
                        brand_id,
                        {
                            "product_id": listing.product_id,
                            "sku_id": str(result.sku_id),
                            "confidence": result.confidence,
                            "method": result.method,
                        },
                    )
                payload_hash = hashlib.sha256(
                    f"{listing.product_id}:{listing.selling_price}:{availability}".encode()
                ).hexdigest()
                for pincode in pins or ["unknown"]:
                    drafts.append(
                        ObservationDraft(
                            brand_id=brand_id,
                            run_id=job.run_id,
                            platform=job.platform,
                            merchant_id=job.merchant_id,
                            pincode=pincode,
                            product_id=listing.product_id,
                            variant_id=listing.variant_id,
                            group_id=listing.group_id,
                            sku_name=listing.sku_name,
                            brand_name=listing.brand_name,
                            pack_raw=listing.pack_raw,
                            pack_ml=pack.pack_ml,
                            category_path=listing.category_path,
                            product_url=listing.product_url,
                            image_url=listing.image_url,
                            mrp=listing.mrp,
                            selling_price=listing.selling_price,
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
                            sku_id=result.sku_id,
                            sku_role=result.sku_role,
                            match_confidence=result.confidence,
                            match_method=result.method,
                            unit_price_per_l=unit_price_per_l(listing.selling_price, pack.pack_ml),
                            unlocker_vendor=vendor,
                            observed_at=now,
                            observed_slot=job.observed_slot,
                            s3_bronze_key=bronze_key,
                            payload_hash=payload_hash,
                        )
                    )
                matched_product_ids.add(listing.product_id)

            for sku in skus:
                if sku.blinkit_product_id and sku.blinkit_product_id not in matched_product_ids:
                    if sku.search_query != query:
                        continue
                    for pincode in pins or ["unknown"]:
                        drafts.append(
                            ObservationDraft(
                                brand_id=sku.brand_id,
                                run_id=job.run_id,
                                platform=job.platform,
                                merchant_id=job.merchant_id,
                                pincode=pincode,
                                product_id=sku.blinkit_product_id,
                                sku_name=sku.display_name,
                                brand_name=sku.brand_name,
                                pack_raw=sku.pack_raw,
                                pack_ml=sku.pack_ml,
                                availability="delisted",
                                sku_id=sku.id,
                                sku_role=sku.sku_role,
                                search_query=query,
                                observed_at=now,
                                observed_slot=job.observed_slot,
                            )
                        )

        self._observations.upsert_many(drafts)
        self._publisher.publish_derive(DeriveJob(run_id=job.run_id))
        return {"status": "ok", "rows": len(drafts), "queries": len(queries)}
