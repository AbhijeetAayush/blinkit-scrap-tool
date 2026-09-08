from datetime import datetime
from typing import Any
from uuid import UUID


def _brand(row: dict[str, Any]) -> UUID | None:
    if not row.get("brand_id"):
        return None
    return UUID(str(row["brand_id"]))


class Alerter:
    def __init__(self, alerts, observations=None) -> None:
        self._alerts = alerts
        self._observations = observations

    def apply(self, rows: list[dict[str, Any]]) -> None:
        self.rival_and_rank(rows)
        self.price_and_rank_vs_previous(rows)

    def rival_and_rank(self, rows: list[dict[str, Any]]) -> None:
        by_pin: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_pin.setdefault(str(row.get("pincode")), []).append(row)
        for pin, group in by_pin.items():
            self_rows = [r for r in group if r.get("sku_role") == "self"]
            rivals = [r for r in group if r.get("sku_role") == "brand_competitor"]
            for mine in self_rows:
                my_unit = mine.get("unit_price_per_l")
                for rival in rivals:
                    ru = rival.get("unit_price_per_l")
                    if my_unit is not None and ru is not None and ru < my_unit:
                        self._alerts.insert(
                            _brand(mine),
                            "rival_cheaper",
                            {
                                "pincode": pin,
                                "self": mine.get("sku_name"),
                                "rival": rival.get("sku_name"),
                            },
                        )

    def price_and_rank_vs_previous(self, rows: list[dict[str, Any]]) -> None:
        if not self._observations:
            return
        for row in rows:
            if row.get("sku_role") != "self":
                continue
            prev = self._observations.get_previous(
                row["platform"],
                row["merchant_id"],
                row["product_id"],
                datetime.fromisoformat(str(row["observed_slot"]).replace("Z", "+00:00")),
            )
            if not prev:
                continue
            brand = _brand(row)
            now_price = row.get("selling_price")
            prev_price = prev.get("selling_price")
            if now_price is not None and prev_price is not None and float(now_price) != float(prev_price):
                self._alerts.insert(
                    brand,
                    "price_change",
                    {
                        "product_id": row.get("product_id"),
                        "from": prev_price,
                        "to": now_price,
                    },
                )
            prev_rank = prev.get("shelf_position") or prev.get("organic_rank")
            now_rank = row.get("shelf_position") or row.get("organic_rank")
            if prev_rank is not None and now_rank is not None and int(now_rank) > int(prev_rank):
                self._alerts.insert(
                    brand,
                    "rank_drop",
                    {
                        "product_id": row.get("product_id"),
                        "from": prev_rank,
                        "to": now_rank,
                    },
                )
