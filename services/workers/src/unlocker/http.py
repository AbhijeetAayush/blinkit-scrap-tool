from __future__ import annotations

import httpx

from src.domain.errors import UnlockerBlockedError

# Must cover ScrapingBee networkidle + wait (~15–25s) plus transfer.
TIMEOUT = httpx.Timeout(connect=15.0, read=90.0, write=15.0, pool=15.0)
RENDER_WAIT_MS = "5000"


def unlocker_get(vendor: str, url: str, *, params: dict[str, str], headers: dict[str, str]) -> httpx.Response:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise UnlockerBlockedError(f"{vendor} {type(exc).__name__}") from exc
    if response.status_code >= 400:
        raise UnlockerBlockedError(f"{vendor} status {response.status_code}")
    return response
