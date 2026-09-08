from __future__ import annotations

import base64
import json
import logging
import secrets
from collections.abc import Callable
from typing import Any

from src.adapters.qstash_verify import verify_with_keys
from src.app.settings import Settings
from src.domain.errors import SignatureError

_LOG = logging.getLogger(__name__)


def function_url_from_event(event: dict[str, Any], fallback: str = "") -> str:
    ctx = event.get("requestContext") or {}
    domain = ctx.get("domainName")
    path = event.get("rawPath") or "/"
    if domain:
        return f"https://{domain}{path}"
    return fallback


def decode_body(event: dict[str, Any]) -> str:
    body = event.get("body")
    if body is None:
        return ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body).decode("utf-8")
    return str(body)


def json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = decode_body(event)
    if not raw:
        return {}
    return json.loads(raw)


def header(event: dict[str, Any], name: str) -> str | None:
    headers = event.get("headers") or {}
    lower = {str(k).lower(): v for k, v in headers.items()}
    return lower.get(name.lower())


def response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=str),
    }


def _is_http_event(event: dict[str, Any]) -> bool:
    ctx = event.get("requestContext") or {}
    return bool(event.get("rawPath") or ctx.get("domainName") or ctx.get("http"))


def _secret_ok(got: str | None, expected: str) -> bool:
    if not got or not expected:
        return False
    left, right = got.encode("utf-8"), expected.encode("utf-8")
    if len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def signed_handler(url_env: str, fn: Callable[[dict[str, Any], str], dict[str, Any]]):
    def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
        settings = Settings.from_env()
        try:
            if isinstance(event, dict) and not _is_http_event(event):
                url = getattr(settings, url_env, "") or ""
                payload = dict(event)
                payload["_self_url"] = url
                return fn(payload, url)

            url = function_url_from_event(event, getattr(settings, url_env, "") or "")
            if _secret_ok(header(event, "x-run-secret"), settings.manual_run_secret):
                payload = json_body(event)
                payload["_self_url"] = url
                return fn(payload, url)

            sig = header(event, "upstash-signature")
            if not sig:
                raise SignatureError("missing signature")
            body = decode_body(event)
            verify_with_keys(
                sig,
                settings.qstash_current_signing_key,
                settings.qstash_next_signing_key,
                body or None,
                url,
            )
            payload = json_body(event)
            payload["_self_url"] = url
            return fn(payload, url)
        except SignatureError as exc:
            return response(401, {"error": str(exc)})
        except Exception:
            _LOG.exception("handler failed")
            return response(500, {"error": "internal"})

    return handler
