"""Deep verification: APIs, bulk CSV path, live scrape, shelf field coverage."""
from __future__ import annotations

import csv
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
BASE = "http://localhost:8000/api/v1"

REQUIRED_CORE = (
    "product_id",
    "sku_name",
    "selling_price",
    "search_query",
    "pincode",
    "merchant_id",
    "availability",
)
RICH_FIELDS = (
    "brand_name",
    "pack_raw",
    "mrp",
    "discount_percent",
    "rating",
    "rating_count",
    "category_path",
    "image_url",
    "product_url",
    "shelf_position",
    "delivery_time_text",
    "unit_price_per_kg",
)


def req(method: str, path: str, data=None, token=None, timeout=90):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if data is None else json.dumps(data).encode()
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"HTTP {e.code} {method} {path}: {detail[:500]}")
        raise


def main() -> int:
    print("== HEALTH ==")
    with urllib.request.urlopen("http://localhost:8000/health", timeout=10) as r:
        print("health", r.read().decode())

    email = f"verify{random.randint(10000, 99999)}@example.com"
    st, reg = req(
        "POST",
        "/auth/register",
        {"email": email, "password": "password123", "workspace_name": "Verify Brand"},
    )
    token = reg["access_token"]
    print("REGISTER", st, email)

    # keywords bulk (slice of real csv)
    kw_path = REPO / "keywords.csv"
    queries: list[str] = []
    with kw_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            q = (row.get("Keyword") or "").strip().lower()
            if len(q) >= 3 and q != "others":
                queries.append(q)
            if len(queries) >= 25:
                break
    st, kw_bulk = req("POST", "/keywords/bulk", {"queries": queries}, token)
    print("KW_BULK", st, kw_bulk)
    st, kw_ids = req("GET", "/keywords/ids?limit=5", token=token)
    print("KW_IDS", st, len(kw_ids.get("ids") or []))

    # locations bulk (real pune file)
    loc_path = REPO / "blinkit_pune_stores.csv"
    locs = []
    with loc_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat = round(float(row["Latitude"]) * 1e6) / 1e6
            lon = round(float(row["Longitude"]) * 1e6) / 1e6
            store = (row.get("Store Name") or "").strip()
            area = (row.get("Area") or "").strip()
            name = f"{store} · {area}" if store and area else (store or area or None)
            locs.append(
                {
                    "platform": "blinkit",
                    "pincode": row["Pincode"].strip(),
                    "lat": lat,
                    "lon": lon,
                    "store_name": name,
                }
            )
    st, loc_bulk = req("POST", "/locations/bulk", {"locations": locs}, token)
    print("LOC_BULK", st, loc_bulk)
    st, loc_ids_resp = req("GET", "/locations/ids?platform=blinkit&limit=5", token=token)
    print("LOC_IDS", st, len(loc_ids_resp.get("ids") or []))

    # pick keyword + one Om Motors-ish location for live scrape
    st, kw_list = req("GET", "/keywords?q=mini%20mogra&limit=5", token=token)
    items = kw_list.get("items") or []
    if not items:
        st, kw = req("POST", "/keywords", {"query": "mini mogra rice"}, token)
        kw_id = kw["id"]
    else:
        kw_id = items[0]["id"]
    print("SCRAPE_KW", kw_id)

    st, loc_list = req("GET", "/locations?q=Om%20Motors&limit=5&platform=blinkit", token=token)
    loc_items = loc_list.get("items") or []
    if not loc_items:
        st, loc = req(
            "POST",
            "/locations",
            {
                "platform": "blinkit",
                "pincode": "411046",
                "store_name": "Om Motors",
                "lat": 18.447819,
                "lon": 73.83708,
            },
            token,
        )
        loc_id = loc["id"]
    else:
        loc_id = loc_items[0]["id"]
    print("SCRAPE_LOC", loc_id)

    st, run = req(
        "POST",
        "/runs",
        {"keyword_ids": [kw_id], "location_ids": [loc_id]},
        token,
    )
    run_id = run["id"]
    print("RUN", run_id, run["status"], "jobs", run.get("jobs_total"))

    status = run["status"]
    last = None
    for i in range(90):
        time.sleep(5)
        st, r = req("GET", f"/runs/{run_id}", token=token)
        status = r["status"]
        snap = (
            status,
            r.get("pages_ok"),
            r.get("pages_fail"),
            r.get("jobs_done"),
            r.get("jobs_total"),
            r.get("error"),
        )
        if snap != last:
            print(
                f"POLL {i}: status={status} ok={r['pages_ok']} fail={r['pages_fail']} "
                f"jobs={r['jobs_done']}/{r['jobs_total']} err={r.get('error')}"
            )
            last = snap
        if status in ("done", "error", "cancelled"):
            for j in r.get("jobs") or []:
                print(" JOB", j.get("status"), j.get("error"))
            break
    else:
        print("TIMEOUT waiting for run")
        return 2

    st, shelf = req("GET", f"/shelf?limit=100&q=mini%20mogra", token=token)
    rows = shelf.get("items") or []
    print("SHELF_COUNT", len(rows))
    if not rows:
        print("FAIL: no shelf rows after scrape")
        return 3

    core_ok = 0
    rich_counts = {f: 0 for f in RICH_FIELDS}
    for row in rows:
        if all(row.get(k) not in (None, "") for k in REQUIRED_CORE):
            core_ok += 1
        for f in RICH_FIELDS:
            val = row.get(f)
            if val is None or val == "" or val == []:
                continue
            rich_counts[f] += 1

    print("CORE_COMPLETE_ROWS", core_ok, "/", len(rows))
    print("RICH_FIELD_COVERAGE")
    for f, n in rich_counts.items():
        pct = 100.0 * n / len(rows)
        print(f"  {f}: {n}/{len(rows)} ({pct:.0f}%)")

    sample = rows[0]
    print("SAMPLE")
    for k in (
        "sku_name",
        "brand_name",
        "category_path",
        "pack_raw",
        "mrp",
        "selling_price",
        "discount_percent",
        "rating",
        "rating_count",
        "shelf_position",
        "is_sponsored",
        "image_url",
        "delivery_time_text",
        "unit_price_per_kg",
        "availability",
    ):
        print(f"  {k}={sample.get(k)!r}")

    # Heuristics for "working enough"
    fail = False
    if status != "done":
        print("FAIL: run status", status)
        fail = True
    if core_ok < max(1, len(rows) // 2):
        print("FAIL: too many rows missing core fields")
        fail = True
    if rich_counts["brand_name"] < 1:
        print("WARN: no brand_name filled")
    if rich_counts["rating"] < 1:
        print("WARN: no ratings filled (JSON may not have been captured)")
    if rich_counts["category_path"] < 1:
        print("WARN: no real categories from Blinkit search JSON (often #-NA only)")
    if rich_counts["unit_price_per_kg"] < 1 and rich_counts["pack_raw"] > 0:
        print("WARN: pack present but unit_price_per_kg empty (check latest_observations view)")
    if len(rows) < 5:
        print("WARN: few products — scroll may not have loaded more than first paint")
    elif len(rows) >= 20:
        print("INFO: scroll loaded", len(rows), "products (lazy-load looks healthy)")

    if fail:
        print("OVERALL: NOT_OK")
        return 1
    print("OVERALL: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
