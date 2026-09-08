from typing import Any


def compute_osa(rows: list[dict[str, Any]]) -> dict[str, float]:
    pins: dict[str, bool] = {}
    pairs_ok = 0
    pairs = 0
    for row in rows:
        pin = row.get("pincode")
        store = row.get("merchant_id")
        in_stock = row.get("availability") == "in_stock"
        key = f"{pin}"
        pins[key] = pins.get(key, False) or in_stock
        pairs += 1
        if in_stock:
            pairs_ok += 1
    consumer = (sum(1 for v in pins.values() if v) / len(pins)) if pins else 0.0
    dark = (pairs_ok / pairs) if pairs else 0.0
    return {"consumer_osa": round(consumer, 4), "dark_store_osa": round(dark, 4)}


def share_of_search(rows: list[dict[str, Any]], n: int = 20) -> float:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row.get("pincode") or ""), str(row.get("search_query") or ""))
        groups.setdefault(key, []).append(row)
    scores: list[float] = []
    for items in groups.values():
        ranked = sorted(items, key=lambda r: r.get("shelf_position") or 999)
        top = ranked[: max(1, n)]
        if not top:
            continue
        owned = sum(1 for r in top if r.get("sku_role") == "self")
        scores.append(owned / len(top))
    return round(sum(scores) / len(scores), 4) if scores else 0.0
