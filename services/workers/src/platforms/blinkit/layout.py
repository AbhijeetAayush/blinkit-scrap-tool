"""Optional Blinkit layout JSON.

Live spike (no ScrapingBee cookies): POST /v1/layout/product/{pid} returned 403 HTML.
Do not call from catalog.search until a cookie-backed payload has rating keyed by product_id.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from src.domain.models import ParsedListing
from src.platforms.blinkit.enrich import enrich_listings
from src.platforms.blinkit.parser import _listing_from_dict, _walk_products

_PRODUCT_URL = "https://blinkit.com/v1/layout/product/{pid}"
_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
_ENRICH_BUDGET_S = 45.0
_MAX_PRODUCTS = 24


def _headers(lat: float | None, lon: float | None, cookies: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "app_client": "consumer_web",
        "Accept": "application/json",
    }
    if lat is not None:
        headers["lat"] = str(lat)
    if lon is not None:
        headers["lon"] = str(lon)
    if cookies:
        headers["Cookie"] = cookies
    return headers


def listings_from_layout_payload(payload: Any, query: str) -> list[ParsedListing]:
    blob: list[dict] = []
    _walk_products(payload, blob)
    out: list[ParsedListing] = []
    seen: set[str] = set()
    for raw in blob:
        item = _listing_from_dict(raw, len(out) + 1, query)
        if not item or item.product_id in seen:
            continue
        seen.add(item.product_id)
        out.append(item)
    return out


def fetch_product_layout(
    pid: str,
    *,
    lat: float | None,
    lon: float | None,
    cookies: str | None = None,
) -> list[ParsedListing] | None:
    """None means blocked/error (stop enrich). [] means HTTP ok but no products."""
    url = _PRODUCT_URL.format(pid=pid)
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.post(url, headers=_headers(lat, lon, cookies), json={})
    except httpx.HTTPError:
        return None
    if resp.status_code in (401, 403, 429):
        return None
    if resp.status_code >= 400:
        return []
    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return []
    return listings_from_layout_payload(payload, "")


def enrich_from_layout(
    listings: list[ParsedListing],
    *,
    lat: float | None,
    lon: float | None,
    cookies: str | None,
) -> list[ParsedListing]:
    missing = [item for item in listings if item.rating is None][:_MAX_PRODUCTS]
    if not missing or lat is None or lon is None:
        return listings
    extras: list[ParsedListing] = []
    deadline = time.monotonic() + _ENRICH_BUDGET_S
    for i, item in enumerate(missing):
        if time.monotonic() > deadline:
            break
        got = fetch_product_layout(item.product_id, lat=lat, lon=lon, cookies=cookies)
        if got is None:
            return listings
        extras.extend(got)
        if i == 0 and not extras:
            continue
    if not extras:
        return listings
    return enrich_listings(listings, extras)
