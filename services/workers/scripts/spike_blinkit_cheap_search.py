"""Phase 0 spike: prove cheap Blinkit search without inventing APIs.

Usage (from services/workers):
  set SCRAPINGBEE_API_KEY=...
  python -m scripts.spike_blinkit_cheap_search

Writes tests/fixtures/blinkit/cheap_search_evidence.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.settings import Settings
from src.domain.errors import ParseEmptyError
from src.platforms.blinkit import constants
from src.platforms.blinkit.catalog import _location_cookies, _location_headers
from src.platforms.blinkit.layout import fetch_product_layout, listings_from_layout_payload
from src.platforms.blinkit.parser import parse_search_html
from src.unlocker.cookies import merge_cookie_header
from src.unlocker.scrapingbee import ScrapingBeeUnlocker

QUERY = "mini mogra rice"
LAT = 18.447818978799855
LON = 73.83707963006026
FIXTURES = ROOT / "tests" / "fixtures" / "blinkit"
EVIDENCE = FIXTURES / "cheap_search_evidence.md"
V1_URL_RE = re.compile(
    r"https://blinkit\.com/v1/[^\s\"'<>]+|/v1/[a-zA-Z0-9_./?-]+",
    re.I,
)


def _settings() -> Settings:
    return Settings.from_env()


def _priced_count(listings) -> int:
    return sum(
        1
        for item in listings
        if item.product_id
        and str(item.product_id).isdigit()
        and item.selling_price is not None
    )


def _write_evidence(
    *,
    winner: str,
    direct_json_method: str,
    direct_json_url_template: str,
    min_listings: int,
    credits_control: float | None,
    credits_cheap: float | None,
    http_status_cheap: int | None,
    notes: str,
) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        "\n".join(
            [
                f"winner: {winner}",
                f"direct_json_method: {direct_json_method}",
                f"direct_json_url_template: {direct_json_url_template}",
                f"min_listings: {min_listings}",
                f"credits_control: {credits_control if credits_control is not None else ''}",
                f"credits_cheap: {credits_cheap if credits_cheap is not None else ''}",
                f"http_status_cheap: {http_status_cheap if http_status_cheap is not None else ''}",
                f"notes: {notes}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {EVIDENCE}")


def main() -> int:
    settings = _settings()
    if not settings.scrapingbee_api_key:
        print("SCRAPINGBEE_API_KEY missing", file=sys.stderr)
        return 2

    bee = ScrapingBeeUnlocker(settings)
    url = constants.SEARCH_URL.format(query=quote(QUERY))
    geo = _location_cookies(LAT, LON, None)
    headers = _location_headers(LAT, LON)

    print("=== 1. control render=True ===")
    control = bee.fetch(url, render=True, country="in", cookies=geo, extra_headers=headers)
    jar = merge_cookie_header(geo, control.cookies)
    control_listings = []
    try:
        control_listings = parse_search_html(control.html, query=QUERY)
    except ParseEmptyError:
        pass
    control_n = _priced_count(control_listings)
    print(
        f"status={control.status_code} credits={control.credits_hint} "
        f"listings={len(control_listings)} priced={control_n} html_len={len(control.html or '')}"
    )
    if control.html and control_n >= 2:
        (FIXTURES / "spike_control_cards.html").write_text(control.html[:400_000], encoding="utf-8")

    # 2. PRELOADED in control HTML (does not save credits)
    preloaded_n = 0
    if control.html:
        from src.platforms.blinkit.parser import _object_after, _walk_products, _listing_from_dict

        for marker in ("window.grofers.PRELOADED_STATE", "window.__PRELOADED_STATE__"):
            state = _object_after(control.html, marker)
            if not state:
                continue
            blob: list[dict] = []
            _walk_products(state, blob)
            seen = set()
            for raw in blob:
                item = _listing_from_dict(raw, len(seen) + 1, QUERY)
                if item and item.product_id not in seen and item.selling_price is not None:
                    seen.add(item.product_id)
            preloaded_n = max(preloaded_n, len(seen))
    print(f"=== 2. preloaded priced in control HTML: {preloaded_n} (not a credit save) ===")

    print("=== 3. Bee render=False with warmed jar ===")
    njs = bee.fetch(url, render=False, country="in", cookies=jar, extra_headers=headers)
    jar = merge_cookie_header(jar, njs.cookies)
    njs_listings = []
    try:
        njs_listings = parse_search_html(njs.html or "", query=QUERY)
    except ParseEmptyError:
        pass
    njs_n = _priced_count(njs_listings)
    print(
        f"status={njs.status_code} credits={njs.credits_hint} "
        f"listings={len(njs_listings)} priced={njs_n} html_len={len(njs.html or '')}"
    )
    if njs.html and njs_n >= 8:
        (FIXTURES / "spike_njs_search.html").write_text(njs.html[:400_000], encoding="utf-8")

    print("=== 4. cookie-backed layout product (not search) ===")
    pid = None
    if control_listings:
        pid = next((x.product_id for x in control_listings if x.product_id and x.product_id.isdigit()), None)
    layout_status = "skipped"
    if pid:
        got = fetch_product_layout(pid, lat=LAT, lon=LON, cookies=jar)
        if got is None:
            layout_status = "blocked_or_error"
        else:
            layout_status = f"ok_listings={len(got)}"
        print(f"pid={pid} layout={layout_status}")
    else:
        print("no pid from control; skip layout")

    print("=== 5. listing JSON only if URL in control HTML ===")
    found_urls: list[str] = []
    if control.html:
        for m in V1_URL_RE.finditer(control.html):
            u = m.group(0)
            if u.startswith("/"):
                u = "https://blinkit.com" + u
            if u not in found_urls:
                found_urls.append(u)
    print(f"v1 urls in HTML: {len(found_urls)}")
    for u in found_urls[:20]:
        print(f"  {u[:160]}")

    direct_winner = False
    direct_method = ""
    direct_template = ""
    direct_status = None
    direct_n = 0
    direct_credits = 0.0

    searchish = [
        u
        for u in found_urls
        if any(k in u.lower() for k in ("search", "listing", "product_listing", "layout/search"))
    ]
    # Prefer search-ish; otherwise skip inventing. Plan: only if listing URL present.
    candidates = searchish[:3]
    if candidates:
        import httpx

        for cand in candidates:
            # Substitute query if placeholder-like; else append q if search path
            try_url = cand
            if "{query}" in try_url:
                try_url = try_url.format(query=quote(QUERY))
            elif "q=" not in try_url and "search" in try_url.lower():
                sep = "&" if "?" in try_url else "?"
                try_url = f"{try_url}{sep}q={quote(QUERY)}"

            hdr = {
                "Content-Type": "application/json",
                "app_client": "consumer_web",
                "Accept": "application/json",
                "lat": str(LAT),
                "lon": str(LON),
            }
            if jar:
                hdr["Cookie"] = jar
            try:
                with httpx.Client(timeout=httpx.Timeout(5.0, read=8.0), follow_redirects=True) as client:
                    resp = client.get(try_url, headers=hdr)
                direct_status = resp.status_code
                if resp.status_code in (401, 403, 429):
                    print(f"GET {try_url[:120]} -> {resp.status_code} blocked")
                    continue
                if resp.status_code >= 400:
                    print(f"GET {try_url[:120]} -> {resp.status_code}")
                    continue
                try:
                    payload = resp.json()
                except json.JSONDecodeError:
                    print(f"GET {try_url[:120]} -> non-json")
                    continue
                listings = listings_from_layout_payload(payload, QUERY)
                n = _priced_count(listings)
                print(f"GET {try_url[:120]} -> {resp.status_code} priced={n}")
                if n >= 8:
                    direct_winner = True
                    direct_method = "GET"
                    direct_template = cand
                    direct_n = n
                    (FIXTURES / "cheap_search.json").write_text(
                        json.dumps(payload)[:500_000],
                        encoding="utf-8",
                    )
                    break
            except Exception as exc:  # noqa: BLE001
                print(f"GET fail {cand[:80]}: {exc}")

    # Decide winner
    winner = "none"
    credits_cheap = None
    http_status_cheap = None
    min_listings = 0
    notes_parts = [
        f"control priced={control_n} credits={control.credits_hint}",
        f"preloaded_in_html={preloaded_n}",
        f"njs priced={njs_n} credits={njs.credits_hint}",
        f"layout={layout_status}",
        f"v1_urls={len(found_urls)} searchish={len(searchish)}",
    ]

    if direct_winner:
        winner = "direct_json"
        min_listings = direct_n
        credits_cheap = direct_credits
        http_status_cheap = direct_status
        notes_parts.append("direct_json from HTML-discovered URL")
    elif njs_n >= 8:
        winner = "bee_njs_html"
        min_listings = njs_n
        credits_cheap = float(njs.credits_hint) if njs.credits_hint is not None else 1.0
        http_status_cheap = njs.status_code
        notes_parts.append("no-JS HTML parseable with warmed jar")
    else:
        notes_parts.append("no cheap path; keep ScrapingBee render=True HTML harvest")

    _write_evidence(
        winner=winner,
        direct_json_method=direct_method,
        direct_json_url_template=direct_template,
        min_listings=min_listings,
        credits_control=float(control.credits_hint) if control.credits_hint is not None else None,
        credits_cheap=credits_cheap,
        http_status_cheap=http_status_cheap,
        notes="; ".join(notes_parts),
    )
    print(f"WINNER={winner}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
