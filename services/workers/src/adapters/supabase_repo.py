from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from src.app.clock import now_utc

from supabase import Client, create_client

from src.app.settings import Settings
from src.domain.models import CoveragePin, Keyword, ObservationDraft, Sku, StoreRef


def _pin(row: dict[str, Any]) -> CoveragePin:
    return CoveragePin(
        id=UUID(str(row["id"])),
        brand_id=UUID(str(row["brand_id"])),
        pincode=row["pincode"],
        city=row.get("city"),
        locality=row.get("locality"),
        store_name=row.get("store_name"),
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        tier=row.get("tier") or "hot",
        platform=row.get("platform") or "blinkit",
        active=bool(row.get("active", True)),
    )


def _sku(row: dict[str, Any]) -> Sku:
    return Sku(
        id=UUID(str(row["id"])),
        brand_id=UUID(str(row["brand_id"])),
        sku_role=row["sku_role"],
        display_name=row["display_name"],
        search_query=row["search_query"],
        brand_name=row["brand_name"],
        pack_raw=row.get("pack_raw"),
        pack_ml=row.get("pack_ml"),
        kvi_flag=bool(row.get("kvi_flag", True)),
        blinkit_product_id=row.get("blinkit_product_id"),
        active=bool(row.get("active", True)),
    )


class SupabaseRepos:
    def __init__(self, settings: Settings) -> None:
        self._client: Client | None = None
        if settings.supabase_url and settings.supabase_service_role_key:
            self._client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def _db(self) -> Client:
        if self._client is None:
            raise RuntimeError("Supabase is not configured")
        return self._client

    def list_active_pins(self, *, offset: int, limit: int) -> list[CoveragePin]:
        res = (
            self._db()
            .table("pincodes")
            .select("*")
            .eq("active", True)
            .order("id")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [_pin(r) for r in (res.data or [])]

    def get_pins_by_ids(self, pincode_ids: list[UUID]) -> list[CoveragePin]:
        rows: list[dict[str, Any]] = []
        ids = [str(i) for i in pincode_ids]
        for i in range(0, len(ids), 100):
            res = self._db().table("pincodes").select("*").in_("id", ids[i : i + 100]).execute()
            rows.extend(res.data or [])
        return [_pin(r) for r in rows]

    def list_keywords_by_ids(self, keyword_ids: list[UUID]) -> list[Keyword]:
        rows: list[Keyword] = []
        ids = [str(i) for i in keyword_ids]
        for i in range(0, len(ids), 100):
            res = self._db().table("keywords").select("*").in_("id", ids[i : i + 100]).execute()
            for row in res.data or []:
                rows.append(
                    Keyword(
                        id=UUID(str(row["id"])),
                        brand_id=UUID(str(row["brand_id"])),
                        query=str(row["query"]),
                        active=bool(row.get("active", True)),
                    )
                )
        return rows

    def list_active_skus(self, brand_id: UUID) -> list[Sku]:
        res = (
            self._db()
            .table("skus")
            .select("*")
            .eq("brand_id", str(brand_id))
            .eq("active", True)
            .execute()
        )
        return [_sku(r) for r in (res.data or [])]

    def list_active_skus_for_merchant(self, platform: str, merchant_id: str) -> list[Sku]:
        mapped = (
            self._db()
            .table("store_map")
            .select("pincode")
            .eq("platform", platform)
            .eq("merchant_id", merchant_id)
            .eq("serviceable", True)
            .execute()
        )
        pins = [r["pincode"] for r in (mapped.data or [])]
        if not pins:
            return []
        cov = (
            self._db()
            .table("pincodes")
            .select("brand_id")
            .eq("platform", platform)
            .eq("active", True)
            .in_("pincode", pins)
            .execute()
        )
        brand_ids = list({r["brand_id"] for r in (cov.data or [])})
        if not brand_ids:
            return []
        res = (
            self._db()
            .table("skus")
            .select("*")
            .eq("active", True)
            .in_("brand_id", brand_ids)
            .execute()
        )
        return [_sku(r) for r in (res.data or [])]

    def brand_ids_for_merchant(self, platform: str, merchant_id: str) -> list[UUID]:
        mapped = (
            self._db()
            .table("store_map")
            .select("pincode")
            .eq("platform", platform)
            .eq("merchant_id", merchant_id)
            .execute()
        )
        pins = [r["pincode"] for r in (mapped.data or [])]
        if not pins:
            return []
        cov = (
            self._db()
            .table("pincodes")
            .select("brand_id")
            .eq("platform", platform)
            .eq("active", True)
            .in_("pincode", pins)
            .execute()
        )
        return list({UUID(str(r["brand_id"])) for r in (cov.data or [])})

    def get(self, platform: str, pincode: str) -> StoreRef | None:
        res = (
            self._db()
            .table("store_map")
            .select("*")
            .eq("platform", platform)
            .eq("pincode", pincode)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        row = rows[0]
        return StoreRef(
            platform=row["platform"],
            merchant_id=row["merchant_id"],
            merchant_type=row.get("merchant_type"),
            serviceable=bool(row.get("serviceable", True)),
            lat=row.get("lat"),
            lon=row.get("lon"),
            city_id=row.get("city_id"),
        )

    def upsert(self, pin: CoveragePin, store: StoreRef) -> None:
        self._db().table("store_map").upsert(
            {
                "platform": store.platform,
                "pincode": pin.pincode,
                "merchant_id": store.merchant_id,
                "merchant_type": store.merchant_type,
                "city_id": store.city_id,
                "serviceable": store.serviceable,
                "lat": store.lat,
                "lon": store.lon,
            }
        ).execute()

    def pins_for_merchant(self, platform: str, merchant_id: str) -> list[str]:
        res = (
            self._db()
            .table("store_map")
            .select("pincode")
            .eq("platform", platform)
            .eq("merchant_id", merchant_id)
            .eq("serviceable", True)
            .execute()
        )
        return [r["pincode"] for r in (res.data or [])]

    def missing_pins(self, pins: list[CoveragePin]) -> list[CoveragePin]:
        missing = []
        for pin in pins:
            mapped = self.get(pin.platform, pin.pincode)
            if mapped is None:
                missing.append(pin)
            elif not mapped.serviceable:
                continue
            elif mapped.merchant_id in {"0", "00", ""}:
                # Invalid merchant id from a bad parse; re-resolve once.
                missing.append(pin)
        return missing

    def upsert_many(self, drafts: list[ObservationDraft]) -> None:
        if not drafts:
            return
        # Postgres rejects ON CONFLICT when the same conflict key appears twice in one statement.
        unique: dict[tuple, ObservationDraft] = {}
        for d in drafts:
            slot = d.observed_slot.isoformat() if d.observed_slot else ""
            key = (d.platform, d.merchant_id, d.pincode, d.product_id, d.search_query or "", slot)
            unique[key] = d
        rows = []
        for d in unique.values():
            payload = d.model_dump(mode="json")
            payload["brand_id"] = str(d.brand_id) if d.brand_id else None
            payload["run_id"] = str(d.run_id) if d.run_id else None
            payload["sku_id"] = str(d.sku_id) if d.sku_id else None
            rows.append(payload)
        for i in range(0, len(rows), 200):
            self._db().table("observations").upsert(
                rows[i : i + 200],
                on_conflict="platform,merchant_id,pincode,product_id,search_query,observed_slot",
            ).execute()

    def list_for_run(self, run_id: UUID) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        page = 1000
        while True:
            res = (
                self._db()
                .table("observations")
                .select("*")
                .eq("run_id", str(run_id))
                .order("id")
                .range(offset, offset + page - 1)
                .execute()
            )
            chunk = list(res.data or [])
            rows.extend(chunk)
            if len(chunk) < page:
                break
            offset += page
        return rows

    def latest_product_ids(self, platform: str, merchant_id: str, search_query: str) -> set[str]:
        res = (
            self._db()
            .table("observations")
            .select("product_id")
            .eq("platform", platform)
            .eq("merchant_id", merchant_id)
            .eq("search_query", search_query)
            .execute()
        )
        return {r["product_id"] for r in (res.data or [])}

    def get_previous(
        self,
        platform: str,
        merchant_id: str,
        product_id: str,
        before_slot: datetime,
    ) -> dict[str, Any] | None:
        res = (
            self._db()
            .table("observations")
            .select("*")
            .eq("platform", platform)
            .eq("merchant_id", merchant_id)
            .eq("product_id", product_id)
            .lt("observed_slot", before_slot.isoformat())
            .order("observed_slot", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def create(
        self,
        *,
        kind: str,
        brand_id: UUID | None,
        correlation_id: str | None,
        continuation_offset: int | None,
    ) -> UUID:
        res = (
            self._db()
            .table("runs")
            .insert(
                {
                    "kind": kind,
                    "brand_id": str(brand_id) if brand_id else None,
                    "correlation_id": correlation_id,
                    "continuation_offset": continuation_offset,
                    "status": "running",
                }
            )
            .execute()
        )
        return UUID(str(res.data[0]["id"]))

    def finish(
        self,
        run_id: UUID,
        *,
        status: str,
        pages_ok: int = 0,
        pages_fail: int = 0,
        credits_hint: float | None = None,
        error: str | None = None,
    ) -> None:
        self._db().table("runs").update(
            {
                "status": status,
                "pages_ok": pages_ok,
                "pages_fail": pages_fail,
                "credits_hint": credits_hint,
                "error": error,
                "finished_at": now_utc().isoformat(),
            }
        ).eq("id", str(run_id)).execute()

    def insert(self, brand_id: UUID | None, alert_type: str, payload: dict[str, Any]) -> None:
        self._db().table("alerts").insert(
            {
                "brand_id": str(brand_id) if brand_id else None,
                "type": alert_type,
                "payload": payload,
            }
        ).execute()

    def insert_match(
        self,
        observation_id: int,
        sku_id: UUID | None,
        relation: str,
        confidence: float,
        method: str,
        decided_by: str,
    ) -> None:
        self._db().table("matches").upsert(
            {
                "observation_id": observation_id,
                "sku_id": str(sku_id) if sku_id else None,
                "relation": relation,
                "confidence": confidence,
                "method": method,
                "decided_by": decided_by,
            },
            on_conflict="observation_id",
        ).execute()

    def open_window(
        self,
        brand_id: UUID,
        sku_id: UUID,
        merchant_id: str,
        started_at: datetime,
        velocity_source: str,
    ) -> None:
        self._db().table("oos_windows").insert(
            {
                "brand_id": str(brand_id),
                "sku_id": str(sku_id),
                "merchant_id": merchant_id,
                "started_at": started_at.isoformat(),
                "velocity_source": velocity_source,
            }
        ).execute()

    def close_open_window(
        self,
        sku_id: UUID,
        merchant_id: str,
        ended_at: datetime,
        psl_inr: float | None,
    ) -> None:
        open_rows = (
            self._db()
            .table("oos_windows")
            .select("*")
            .eq("sku_id", str(sku_id))
            .eq("merchant_id", merchant_id)
            .is_("ended_at", "null")
            .execute()
        )
        for row in open_rows.data or []:
            started = datetime.fromisoformat(str(row["started_at"]).replace("Z", "+00:00"))
            hours = (ended_at - started).total_seconds() / 3600.0
            self._db().table("oos_windows").update(
                {
                    "ended_at": ended_at.isoformat(),
                    "duration_hours": hours,
                    "psl_inr": psl_inr,
                }
            ).eq("id", row["id"]).execute()

    def get_velocity(self, sku_id: UUID) -> tuple[float, str] | None:
        res = (
            self._db()
            .table("sku_velocity")
            .select("*")
            .eq("sku_id", str(sku_id))
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        return float(rows[0]["units_per_store_day"]), str(rows[0].get("source") or "tenant")

    def insert_review(self, brand_id: UUID, payload: dict[str, Any]) -> None:
        self._db().table("review_queue").insert(
            {"brand_id": str(brand_id), "payload": payload}
        ).execute()

    def list_open(self) -> list[dict[str, Any]]:
        res = (
            self._db()
            .table("oos_windows")
            .select("*")
            .is_("ended_at", "null")
            .execute()
        )
        return list(res.data or [])
