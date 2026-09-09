from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from src.app.settings import Settings
from src.domain.models import DeriveJob, ScrapeJob


class QStashPublisher:
    def __init__(self, settings: Settings) -> None:
        self._token = settings.qstash_token
        self._qstash_url = (settings.qstash_url or "https://qstash.upstash.io").rstrip("/")
        self._scrape_url = settings.scrape_function_url
        self._derive_url = settings.derive_function_url
        self._resolve_url = settings.resolve_function_url
        self._dispatch_url = settings.dispatch_function_url
        self._scrape_name = settings.scrape_function_name
        self._derive_name = settings.derive_function_name
        self._resolve_name = settings.resolve_function_name
        self._dispatch_name = settings.dispatch_function_name

    def _qstash_ok(self) -> bool:
        return bool(self._token) and self._token.count(".") == 2

    def _name_for(self, destination: str) -> str:
        dest = (destination or "").rstrip("/")
        if dest and "://" not in dest:
            return dest
        pairs = (
            (self._scrape_url, self._scrape_name),
            (self._derive_url, self._derive_name),
            (self._resolve_url, self._resolve_name),
            (self._dispatch_url, self._dispatch_name),
        )
        for url, name in pairs:
            if url and dest == url.rstrip("/") and name:
                return name
        fallback = self._dispatch_name or os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
        if fallback and "://" not in fallback:
            return fallback
        raise RuntimeError("lambda invoke target missing")

    def _invoke(self, destination: str, payload: dict[str, Any]) -> None:
        import boto3

        name = self._name_for(destination)
        if not name:
            raise RuntimeError("lambda invoke target missing")
        boto3.client("lambda").invoke(
            FunctionName=name,
            InvocationType="Event",
            Payload=json.dumps(payload, default=str).encode(),
        )

    def _post(self, destination: str, payload: dict[str, Any], delay_s: int = 0) -> None:
        dest = (destination or "").strip()
        if not dest:
            return
        if not self._qstash_ok():
            self._invoke(dest, payload)
            return
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        if delay_s > 0:
            headers["Upstash-Delay"] = f"{delay_s}s"
        url = f"{self._qstash_url}/v2/publish/{quote(dest, safe='')}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, content=json.dumps(payload, default=str))
        if resp.status_code >= 400:
            raise RuntimeError(f"qstash publish failed status={resp.status_code} body={resp.text[:300]}")

    def publish_scrape(self, job: ScrapeJob, delay_s: int) -> None:
        payload: dict[str, Any] = {
            "brand_ids": [str(b) for b in job.brand_ids],
            "brand_id": str(job.brand_id) if job.brand_id else None,
            "merchant_id": job.merchant_id,
            "platform": job.platform,
            "run_id": str(job.run_id),
            "correlation_id": job.correlation_id,
            "observed_slot": job.observed_slot.isoformat(),
            "queries": list(job.queries or []),
            "pincode": job.pincode,
            "lat": job.lat,
            "lon": job.lon,
        }
        self._post(self._scrape_url or self._scrape_name, payload, delay_s)

    def publish_derive(self, job: DeriveJob) -> None:
        self._post(self._derive_url or self._derive_name, {"run_id": str(job.run_id)})

    def publish_resolve(self, payload: dict[str, Any]) -> None:
        self._post(self._resolve_url or self._resolve_name, payload)

    def publish_dispatch_continuation(
        self,
        offset: int,
        run_id: UUID,
        observed_slot: datetime,
        slot_kind: str,
        self_url: str,
        *,
        brand_id: UUID | None = None,
        keyword_ids: list[UUID] | None = None,
        pincode_ids: list[UUID] | None = None,
    ) -> None:
        dest = self_url or self._dispatch_url or self._dispatch_name
        body: dict[str, Any] = {
            "continuation_offset": offset,
            "observed_slot": observed_slot.isoformat(),
            "run_id": str(run_id),
            "slot_kind": slot_kind,
            "brand_id": str(brand_id) if brand_id else None,
            "keyword_ids": [str(i) for i in (keyword_ids or [])],
            "pincode_ids": [str(i) for i in (pincode_ids or [])],
        }
        self._post(dest, body, delay_s=2)
