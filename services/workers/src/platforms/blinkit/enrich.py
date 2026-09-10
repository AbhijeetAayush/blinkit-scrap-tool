from __future__ import annotations

from src.domain.models import ParsedListing

_HTML_WINS = ("selling_price", "mrp", "shelf_position", "discount_text", "pack_raw")


def enrich_listings(html_listings: list[ParsedListing], extras: list[ParsedListing]) -> list[ParsedListing]:
    """Fill nulls from JSON. HTML keeps on-page price, rank, pack, discount text."""
    by_id = {item.product_id: item for item in extras if item.product_id}
    out: list[ParsedListing] = []
    for base in html_listings:
        extra = by_id.get(base.product_id)
        if not extra:
            out.append(base)
            continue
        data = base.model_dump()
        extra_data = extra.model_dump()
        for key, value in extra_data.items():
            if key in _HTML_WINS and data.get(key) not in (None, "", []):
                continue
            if data.get(key) in (None, "", []) and value not in (None, "", []):
                data[key] = value
        out.append(ParsedListing(**data))
    return out
