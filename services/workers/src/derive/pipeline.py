from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.derive.alerts import Alerter
from src.derive.oos import OosTracker
from src.derive.osa import compute_osa, share_of_search
from src.derive.psl import predicted_sales_loss


class DerivePipeline:
    def __init__(self, observations, lake, oos: OosTracker, alerter: Alerter, settings, runs=None) -> None:
        self._observations = observations
        self._lake = lake
        self._oos = oos
        self._alerter = alerter
        self._settings = settings
        self._runs = runs

    def run(self, run_id: UUID) -> dict[str, Any]:
        rows = self._observations.list_for_run(run_id)
        self._persist_matches(rows)
        self._oos.apply(rows)
        osa = compute_osa(rows)
        sos = share_of_search(rows, self._settings.share_of_search_n)
        self._alerter.apply(rows)
        now = datetime.now(timezone.utc)
        key = f"silver/platform=blinkit/dt={now.date().isoformat()}/run={run_id}.jsonl"
        body = "\n".join(json.dumps(r, default=str) for r in rows).encode()
        self._lake.put_silver(key, body)
        oos_rows = [r for r in rows if r.get("availability") == "oos"]
        oos_stores = len({r["merchant_id"] for r in oos_rows})
        prices = [float(r["selling_price"]) for r in oos_rows if r.get("selling_price") is not None]
        avg_price = (sum(prices) / len(prices)) if prices else 0.0
        psl = predicted_sales_loss(self._settings.default_velocity, oos_stores, 1.0, avg_price)
        if self._runs:
            self._runs.finish(run_id, status="derived", pages_ok=len(rows), credits_hint=None)
        return {"rows": len(rows), "osa": osa, "share_of_search": sos, "psl": psl}

    def _persist_matches(self, rows: list[dict[str, Any]]) -> None:
        insert = getattr(self._observations, "insert_match", None)
        if not insert:
            return
        for row in rows:
            if not row.get("sku_id") or not row.get("id"):
                continue
            relation = "like_item" if row.get("sku_role") == "brand_competitor" else "exact"
            insert(
                int(row["id"]),
                UUID(str(row["sku_id"])),
                relation,
                float(row.get("match_confidence") or 0),
                str(row.get("match_method") or "derive"),
                "derive",
            )
