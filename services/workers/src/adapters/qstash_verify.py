from __future__ import annotations

import base64
import hashlib
import hmac
import time

import jwt

from src.domain.errors import SignatureError


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def verify(jwt_token: str, signing_key: str, body: str | None, url: str) -> None:
    parts = jwt_token.split(".")
    if len(parts) != 3:
        raise SignatureError("Invalid JWT.")
    header, payload, signature = parts
    message = f"{header}.{payload}"
    generated = _b64url(hmac.new(signing_key.encode(), message.encode(), hashlib.sha256).digest())
    if generated != signature and generated + "=" != signature and signature + "=" != generated:
        if generated != signature.rstrip("="):
            raise SignatureError("Invalid JWT signature.")

    decoded = jwt.decode(jwt_token, options={"verify_signature": False})
    if decoded.get("iss") != "Upstash":
        raise SignatureError("Invalid issuer")
    sub = str(decoded.get("sub") or "").rstrip("/")
    if sub != url.rstrip("/"):
        raise SignatureError("Invalid subject")
    now = time.time()
    if now > float(decoded.get("exp", 0)):
        raise SignatureError("Token has expired.")
    if now < float(decoded.get("nbf", 0)):
        raise SignatureError("Token is not yet valid.")
    if body is not None:
        expected = _b64url(hashlib.sha256(body.encode()).digest())
        token_body = str(decoded.get("body") or "").rstrip("=")
        if expected.rstrip("=") != token_body:
            raise SignatureError("Body hash doesn't match.")


def verify_with_keys(jwt_token: str, current: str, nxt: str, body: str | None, url: str) -> None:
    try:
        verify(jwt_token, current, body, url)
    except SignatureError:
        verify(jwt_token, nxt, body, url)
