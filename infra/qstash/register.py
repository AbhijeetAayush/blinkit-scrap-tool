"""QStash schedule registration. Run after `sam deploy` using stack Outputs.

Example:
  set QSTASH_TOKEN=...
  python infra/qstash/register.py --dispatch-url https://xxx.lambda-url.us-east-1.on.aws/ --resolve-url https://yyy.lambda-url.us-east-1.on.aws/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import quote

import httpx

API = os.environ.get("QSTASH_URL", "https://qstash.upstash.io").rstrip("/") + "/v2/schedules"


def upsert(token: str, destination: str, cron: str, body: dict, schedule_id: str) -> None:
    dest = destination.rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Upstash-Cron": cron,
        "Upstash-Retries": "3",
        "Upstash-Schedule-Id": schedule_id,
        "Upstash-Schedule-Timezone": "Asia/Kolkata",
    }
    url = f"{API}/{quote(dest, safe='')}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, content=json.dumps(body))
        resp.raise_for_status()
        print(schedule_id, resp.status_code, resp.text[:200])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dispatch-url", required=True)
    parser.add_argument("--resolve-url", required=True)
    parser.add_argument("--token", default=os.environ.get("QSTASH_TOKEN", ""))
    args = parser.parse_args()
    if not args.token:
        print("QSTASH_TOKEN missing", file=sys.stderr)
        return 1
    upsert(args.token, args.dispatch_url, "0 9 * * *", {"slot_kind": "morning"}, "dispatch-morning")
    upsert(args.token, args.dispatch_url, "0 19 * * *", {"slot_kind": "evening"}, "dispatch-evening")
    upsert(args.token, args.resolve_url, "0 6 * * *", {"pincode_ids": []}, "resolve-stores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
