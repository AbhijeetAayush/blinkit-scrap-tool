from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from src.app.settings import Settings


class RedisCache:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.upstash_redis_url.rstrip("/")
        self._token = settings.upstash_redis_token
        self._budget = settings.daily_credit_budget

    def _cmd(self, *parts: str) -> httpx.Response | None:
        if not self._url or not self._token:
            return None
        path = "/".join(quote(p, safe="") for p in parts)
        with httpx.Client(timeout=15.0) as client:
            return client.get(
                f"{self._url}/{path}",
                headers={"Authorization": f"Bearer {self._token}"},
            )

    def acquire(self, key: str, ttl_s: int) -> bool:
        resp = self._cmd("SET", key, "1", "NX", "EX", str(ttl_s))
        if resp is None:
            return True
        data = resp.json()
        return data.get("result") == "OK"

    def release(self, key: str) -> None:
        self._cmd("DEL", key)

    def set_halt(self, run_id: str, ttl_s: int = 3600) -> None:
        self._cmd("SET", f"run:{run_id}:halt", "1", "EX", str(ttl_s))

    def is_halted(self, run_id: str) -> bool:
        resp = self._cmd("GET", f"run:{run_id}:halt")
        if resp is None:
            return False
        return bool(resp.json().get("result"))

    def cache_store(self, platform: str, pincode: str, payload: str, ttl_s: int = 86400) -> None:
        self._cmd("SET", f"store_map:{platform}:{pincode}", payload, "EX", str(ttl_s))

    def get_session(self, platform: str, merchant_id: str, vendor: str) -> str | None:
        resp = self._cmd("GET", f"session:{platform}:{merchant_id}:{vendor}")
        if resp is None:
            return None
        raw = resp.json().get("result")
        return str(raw) if raw else None

    def set_session(
        self,
        platform: str,
        merchant_id: str,
        vendor: str,
        cookies: str,
        ttl_s: int = 1200,
    ) -> None:
        self._cmd("SET", f"session:{platform}:{merchant_id}:{vendor}", cookies, "EX", str(ttl_s))

    def add(self, n: float) -> None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._cmd("INCRBYFLOAT", f"credits:day:{day}", str(n))

    def remaining(self) -> float:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        resp = self._cmd("GET", f"credits:day:{day}")
        used = 0.0
        if resp is not None:
            raw = resp.json().get("result")
            if raw is not None:
                used = float(raw)
        return float(self._budget) - used
