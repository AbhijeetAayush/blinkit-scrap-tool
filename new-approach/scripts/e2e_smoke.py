import json
import random
import time
import urllib.error
import urllib.request

base = "http://localhost:8000/api/v1"


def req(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if data is None else json.dumps(data).encode()
    r = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode())
        raise


email = f"test{random.randint(10000, 99999)}@example.com"
reg = req(
    "POST",
    "/auth/register",
    {"email": email, "password": "password123", "workspace_name": "Demo Brand"},
)
token = reg["access_token"]
print("REGISTER ok", email)

kw = req("POST", "/keywords", {"query": "mini mogra rice"}, token)
print("KEYWORD", kw["id"], kw["query"])

loc = req(
    "POST",
    "/locations",
    {
        "platform": "blinkit",
        "pincode": "411046",
        "store_name": "Om Motors",
        "lat": 18.447818978799855,
        "lon": 73.83707963006026,
    },
    token,
)
print("LOCATION", loc["id"])

run = req(
    "POST",
    "/runs",
    {"keyword_ids": [kw["id"]], "location_ids": [loc["id"]]},
    token,
)
run_id = run["id"]
print("RUN", run_id, run["status"], "jobs", run["jobs_total"])

status = run["status"]
for i in range(72):
    time.sleep(5)
    r = req("GET", f"/runs/{run_id}", token=token)
    status = r["status"]
    print(
        f"POLL {i}: status={status} ok={r['pages_ok']} fail={r['pages_fail']} "
        f"jobs={r['jobs_done']}/{r['jobs_total']}"
    )
    if status in ("done", "error", "cancelled"):
        if r.get("jobs"):
            for j in r["jobs"]:
                print(" JOB", j.get("status"), j.get("error"))
        break

shelf = req("GET", "/shelf?limit=50", token=token)
items = shelf.get("items") or []
print("SHELF_COUNT", len(items))
for row in items[:8]:
    print(" ", row.get("sku_name"), row.get("selling_price"), row.get("product_id"))
print("FINAL", status)
