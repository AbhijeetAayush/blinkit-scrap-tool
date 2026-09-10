"""One-shot probe: capture Blinkit search JSON keys related to category/rating."""
from __future__ import annotations

import asyncio
import json
from collections import Counter

from app.config import get_settings
from app.infrastructure.browser.playwright_factory import launch_session
from app.platforms.blinkit.browser import fetch_search_page
from app.platforms.blinkit.parser import parse_search_html


def walk_keys(obj, acc: Counter, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("categor", "rating", "l0", "l1", "l2", "type")):
                acc[f"{path}.{k}" if path else k] += 1
                if isinstance(v, (str, int, float)) or v is None:
                    acc[f"VAL::{k}={v!r}"] += 1
            walk_keys(v, acc, path=f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:20]):
            walk_keys(item, acc, path=path)


async def main() -> None:
    get_settings.cache_clear()
    async with launch_session(session_id="probe") as session:
        html, payloads = await fetch_search_page(
            session,
            "mini mogra rice",
            lat=18.447819,
            lon=73.83708,
        )
        listings = parse_search_html(html, query="mini mogra rice", json_payloads=payloads)
        print("PAYLOADS", len(payloads), "HTML_LEN", len(html), "LISTINGS", len(listings))
        with_rating = sum(1 for x in listings if x.rating is not None)
        with_cat = sum(1 for x in listings if x.category_path)
        print("WITH_RATING", with_rating, "WITH_CATEGORY", with_cat)
        if listings:
            s = listings[0]
            print(
                "SAMPLE",
                s.sku_name,
                s.rating,
                s.rating_count,
                s.category_path,
                s.pack_raw,
                s.unit_price_per_kg if hasattr(s, "unit_price_per_kg") else None,
            )
        keys: Counter = Counter()
        for p in payloads:
            walk_keys(p, keys)
        print("TOP_CATEGORY_RATING_KEYS")
        for k, n in keys.most_common(40):
            if k.startswith("VAL::"):
                print(" ", k)
            else:
                print(f"  {k}: {n}")
        # dump tiny slice for inspection
        Path = __import__("pathlib").Path
        out = Path("/tmp/blinkit_payload_sample.json")
        out.write_text(json.dumps(payloads[:2], default=str)[:200000], encoding="utf-8")
        print("WROTE", out, "bytes", out.stat().st_size)


if __name__ == "__main__":
    asyncio.run(main())
