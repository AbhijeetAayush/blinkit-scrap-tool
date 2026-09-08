from datetime import datetime
from typing import Any
from uuid import UUID


class OosTracker:
    def __init__(self, observations, oos_repo, velocity_repo, default_velocity: float, alerts=None) -> None:
        self._observations = observations
        self._oos = oos_repo
        self._velocity = velocity_repo
        self._default_velocity = default_velocity
        self._alerts = alerts

    def apply(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            sku_id = row.get("sku_id")
            if not sku_id:
                continue
            prev = self._observations.get_previous(
                row["platform"],
                row["merchant_id"],
                row["product_id"],
                datetime.fromisoformat(str(row["observed_slot"]).replace("Z", "+00:00")),
            )
            prev_avail = (prev or {}).get("availability")
            now_avail = row.get("availability")
            brand_id = row.get("brand_id")
            if not brand_id:
                continue
            if prev_avail == "in_stock" and now_avail == "oos":
                vel = self._velocity.get(UUID(str(sku_id)))
                source = vel[1] if vel else "default"
                self._oos.open_window(
                    UUID(str(brand_id)),
                    UUID(str(sku_id)),
                    row["merchant_id"],
                    datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00")),
                    source,
                )
                if self._alerts:
                    self._alerts.insert(
                        UUID(str(brand_id)),
                        "oos",
                        {
                            "sku_id": str(sku_id),
                            "merchant_id": row["merchant_id"],
                            "product_id": row.get("product_id"),
                        },
                    )
            if prev_avail == "oos" and now_avail == "in_stock":
                vel = self._velocity.get(UUID(str(sku_id)))
                units = vel[0] if vel else self._default_velocity
                price = float(row.get("selling_price") or 0)
                self._oos.close_open_window(
                    UUID(str(sku_id)),
                    row["merchant_id"],
                    datetime.fromisoformat(str(row["observed_at"]).replace("Z", "+00:00")),
                    psl_inr=units * price / 24.0,
                )
