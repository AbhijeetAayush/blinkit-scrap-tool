from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str
    zenrows_api_key: str
    scrapingbee_api_key: str
    upstash_redis_url: str
    upstash_redis_token: str
    qstash_token: str
    qstash_url: str
    qstash_current_signing_key: str
    qstash_next_signing_key: str
    unlocker_search: str
    unlocker_location: str
    unlocker_failover: bool
    daily_credit_budget: int
    fail_fast: bool
    scrape_spread_seconds: int
    default_velocity: float
    max_stores_per_dispatch: int
    match_auto_commit: float
    share_of_search_n: int
    pin_page_size: int
    s3_bucket: str
    scrape_function_url: str
    derive_function_url: str
    resolve_function_url: str
    dispatch_function_url: str
    scrape_function_name: str
    derive_function_name: str
    resolve_function_name: str
    dispatch_function_name: str
    manual_run_secret: str

    @property
    def credit_budget(self) -> int:
        return self.daily_credit_budget

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            supabase_url=os.environ.get("SUPABASE_URL", ""),
            supabase_service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            zenrows_api_key=os.environ.get("ZENROWS_API_KEY", ""),
            scrapingbee_api_key=os.environ.get("SCRAPINGBEE_API_KEY", ""),
            upstash_redis_url=os.environ.get("UPSTASH_REDIS_URL", ""),
            upstash_redis_token=os.environ.get("UPSTASH_REDIS_TOKEN", ""),
            qstash_token=os.environ.get("QSTASH_TOKEN", ""),
            qstash_url=os.environ.get("QSTASH_URL", "https://qstash.upstash.io").rstrip("/"),
            qstash_current_signing_key=os.environ.get("QSTASH_CURRENT_SIGNING_KEY", ""),
            qstash_next_signing_key=os.environ.get("QSTASH_NEXT_SIGNING_KEY", ""),
            unlocker_search=os.environ.get("UNLOCKER_SEARCH", "scrapingbee"),
            unlocker_location=os.environ.get("UNLOCKER_LOCATION", "scrapingbee"),
            unlocker_failover=_as_bool(os.environ.get("UNLOCKER_FAILOVER"), True),
            daily_credit_budget=_as_int(os.environ.get("DAILY_CREDIT_BUDGET"), 400),
            fail_fast=_as_bool(os.environ.get("FAIL_FAST"), True),
            scrape_spread_seconds=_as_int(os.environ.get("SCRAPE_SPREAD_SECONDS"), 3),
            default_velocity=_as_float(os.environ.get("DEFAULT_VELOCITY"), 5.0),
            max_stores_per_dispatch=_as_int(os.environ.get("MAX_STORES_PER_DISPATCH"), 500),
            match_auto_commit=_as_float(os.environ.get("MATCH_AUTO_COMMIT"), 0.95),
            share_of_search_n=_as_int(os.environ.get("SHARE_OF_SEARCH_N"), 20),
            pin_page_size=_as_int(os.environ.get("PIN_PAGE_SIZE"), 500),
            s3_bucket=os.environ.get("S3_BUCKET", ""),
            scrape_function_url=os.environ.get("SCRAPE_FUNCTION_URL", ""),
            derive_function_url=os.environ.get("DERIVE_FUNCTION_URL", ""),
            resolve_function_url=os.environ.get("RESOLVE_FUNCTION_URL", ""),
            dispatch_function_url=os.environ.get("DISPATCH_FUNCTION_URL", ""),
            scrape_function_name=os.environ.get("SCRAPE_FUNCTION_NAME", ""),
            derive_function_name=os.environ.get("DERIVE_FUNCTION_NAME", ""),
            resolve_function_name=os.environ.get("RESOLVE_FUNCTION_NAME", ""),
            dispatch_function_name=os.environ.get("DISPATCH_FUNCTION_NAME") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME", ""),
            manual_run_secret=os.environ.get("MANUAL_RUN_SECRET", ""),
        )
