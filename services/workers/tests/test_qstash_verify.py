import json

from src.adapters.qstash_verify import verify
from src.aws.http import signed_handler
from src.domain.errors import SignatureError


def test_invalid_signature_raises():
    try:
        verify("not-a-jwt", "signing-key", "{}", "https://example.lambda-url.ap-south-1.on.aws/")
        raise AssertionError("expected SignatureError")
    except SignatureError:
        pass


def test_unsigned_handler_returns_401(monkeypatch):
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", "current")
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", "next")

    def inner(_payload, _url):
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": "{}"}

    handler = signed_handler("dispatch_function_url", inner)
    result = handler({"headers": {}, "body": "{}", "requestContext": {"domainName": "example.lambda-url.ap-south-1.on.aws"}, "rawPath": "/"})
    assert result["statusCode"] == 401


def test_run_secret_skips_jwt(monkeypatch):
    monkeypatch.setenv("MANUAL_RUN_SECRET", "test-secret")

    def inner(payload, _url):
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(payload)}

    handler = signed_handler("dispatch_function_url", inner)
    result = handler(
        {
            "headers": {"x-run-secret": "test-secret"},
            "body": '{"slot_kind":"manual"}',
            "requestContext": {"domainName": "example.lambda-url.us-east-1.on.aws"},
            "rawPath": "/",
        }
    )
    assert result["statusCode"] == 200


def test_publisher_maps_url_to_function_name():
    from src.adapters.qstash_publisher import QStashPublisher
    from src.app.settings import Settings

    settings = Settings(
        supabase_url="",
        supabase_service_role_key="",
        zenrows_api_key="",
        scrapingbee_api_key="",
        upstash_redis_url="",
        upstash_redis_token="",
        qstash_token="not-a-jwt",
        qstash_url="https://qstash-us-east-1.upstash.io",
        qstash_current_signing_key="",
        qstash_next_signing_key="",
        unlocker_search="zenrows",
        unlocker_location="scrapingbee",
        unlocker_failover=True,
        daily_credit_budget=400,
        fail_fast=True,
        scrape_spread_seconds=3,
        default_velocity=5.0,
        max_stores_per_dispatch=500,
        match_auto_commit=0.95,
        share_of_search_n=20,
        pin_page_size=500,
        s3_bucket="",
        scrape_function_url="https://scrape.example",
        derive_function_url="https://derive.example",
        resolve_function_url="https://resolve.example",
        dispatch_function_url="",
        scrape_function_name="scrap-Scrape",
        derive_function_name="scrap-Derive",
        resolve_function_name="scrap-Resolve",
        dispatch_function_name="",
        manual_run_secret="",
    )
    pub = QStashPublisher(settings)
    assert pub._name_for("https://scrape.example") == "scrap-Scrape"


def test_direct_invoke_skips_jwt(monkeypatch):
    def inner(payload, _url):
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"ok": payload.get("slot_kind")})}

    handler = signed_handler("dispatch_function_url", inner)
    result = handler({"slot_kind": "manual"})
    assert result["statusCode"] == 200
