"""Cookie jar helpers: never drop job lat/lon when Set-Cookie arrives."""

from __future__ import annotations

_KEEP = ("gr_1_lat", "gr_1_lon", "lat", "lon")


def _pairs(header: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not header:
        return out
    for part in header.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        name = key.strip().lower()
        if name in {"path", "domain", "expires", "max-age", "samesite", "secure", "httponly"}:
            continue
        out[name] = value.strip()
    return out


def merge_cookie_header(existing: str | None, incoming: str | None) -> str | None:
    base = _pairs(existing)
    new = _pairs(incoming)
    merged = {**base, **new}
    for key in _KEEP:
        if key in base:
            merged[key] = base[key]
    if not merged:
        return incoming or existing
    return "; ".join(f"{k}={v}" for k, v in merged.items())
