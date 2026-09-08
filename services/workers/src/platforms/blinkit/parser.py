from __future__ import annotations

import json
import re
from urllib.parse import unquote

from selectolax.parser import HTMLParser

from src.domain.errors import ParseEmptyError
from src.domain.models import ParsedListing

_JSON_LD = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
_EMBEDDED = re.compile(r"window\.__PRELOADED_STATE__\s*=\s*({.*?});", re.S)
_PRICE = re.compile(r"(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)")
_PACK = re.compile(r"(\d+(?:\.\d+)?\s?(?:kg|g|ml|l|pcs|pc|pack))\b", re.I)
_ETA = re.compile(r"(\d+)\s*mins?", re.I)
_OFF = re.compile(r"\d+%\s*OFF", re.I)


def _object_after(html: str, marker: str) -> dict | None:
    idx = html.find(marker)
    if idx < 0:
        return None
    start = html.find("{", idx)
    if start < 0:
        return None
    try:
        obj, _n = json.JSONDecoder().raw_decode(html[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _text(node) -> str:
    return " ".join((node.text(separator=" ") or "").split()) if node else ""


def _listing_from_dict(raw: dict, position: int, query: str) -> ParsedListing | None:
    product_id = str(raw.get("product_id") or raw.get("productId") or "")
    name = raw.get("name") or raw.get("title") or raw.get("sku_name")
    if isinstance(name, dict):
        name = name.get("text") or name.get("value")
    if not product_id or not isinstance(name, str) or not name:
        return None
    price = raw.get("price") or raw.get("selling_price") or raw.get("offer_price")
    mrp = raw.get("mrp")
    in_stock = raw.get("in_stock")
    if in_stock is None:
        in_stock = not bool(raw.get("out_of_stock") or raw.get("is_sold_out"))
    return ParsedListing(
        product_id=product_id,
        variant_id=str(raw.get("variant_id") or raw.get("variantId") or product_id),
        group_id=str(raw.get("group_id") or "") or None,
        sku_name=str(name),
        brand_name=raw.get("brand") or raw.get("brand_name"),
        pack_raw=raw.get("unit") or raw.get("quantity") or raw.get("pack"),
        mrp=float(mrp) if mrp is not None else None,
        selling_price=float(price) if price is not None else None,
        in_stock=bool(in_stock),
        inventory_shown=int(raw["inventory"]) if raw.get("inventory") is not None else None,
        qty_cap=int(raw["max_qty"]) if raw.get("max_qty") is not None else (
            int(raw["max_allowed_quantity"]) if raw.get("max_allowed_quantity") is not None else None
        ),
        is_sponsored=raw.get("is_ad") if raw.get("is_ad") is not None else raw.get("is_sponsored"),
        shelf_position=int(raw.get("position") or position),
        organic_rank=int(raw["organic_rank"]) if raw.get("organic_rank") is not None else None,
        rating=float(raw["rating"]) if raw.get("rating") is not None else None,
        rating_count=int(raw["rating_count"]) if raw.get("rating_count") is not None else None,
        image_url=(raw.get("image_url") or (raw.get("images") or [None])[0]),
        product_url=raw.get("product_url") or raw.get("deeplink"),
        offer_text=raw.get("offer_text") or raw.get("discount"),
        discount_text=raw.get("discount"),
        delivery_promise_min=int(raw["eta_minutes"]) if raw.get("eta_minutes") is not None else None,
        delivery_time_text=raw.get("delivery_time"),
        category_path=[p for p in [raw.get("l0_category"), raw.get("l1_category"), raw.get("sub_category")] if p],
        search_query=query,
    )


def _walk_products(obj, acc: list[dict]) -> None:
    if isinstance(obj, dict):
        if "product_id" in obj or "productId" in obj or (
            "name" in obj and ("price" in obj or "mrp" in obj)
        ):
            acc.append(obj)
        for value in obj.values():
            _walk_products(value, acc)
    elif isinstance(obj, list):
        for item in obj:
            _walk_products(item, acc)


def parse_search_html(html: str, query: str = "") -> list[ParsedListing]:
    listings: list[ParsedListing] = []
    seen: set[str] = set()

    for match in _JSON_LD.finditer(html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        blob: list[dict] = []
        _walk_products(data, blob)
        for raw in blob:
            item = _listing_from_dict(raw, len(listings) + 1, query)
            if item and item.product_id not in seen:
                seen.add(item.product_id)
                listings.append(item)

    embedded = _EMBEDDED.search(html)
    if embedded:
        try:
            data = json.loads(embedded.group(1))
            blob = []
            _walk_products(data, blob)
            for raw in blob:
                item = _listing_from_dict(raw, len(listings) + 1, query)
                if item and item.product_id not in seen:
                    seen.add(item.product_id)
                    listings.append(item)
        except json.JSONDecodeError:
            pass

    tree = HTMLParser(html)
    for card in tree.css("div[role='button'][id]"):
        pid = (card.attributes.get("id") or "").strip()
        if not pid.isdigit() or pid in seen:
            continue
        item = _listing_from_card(card, len(listings) + 1, query)
        if item:
            seen.add(item.product_id)
            listings.append(item)

    cards = tree.css("[data-product-id], [data-product], .product-card, article")
    for idx, card in enumerate(cards, start=1):
        pid = card.attributes.get("data-product-id") or card.attributes.get("data-product") or ""
        name_el = card.css_first("[data-testid='product-name'], .product-name, h2, h3")
        name = _text(name_el)
        if not pid and name:
            pid = unquote(card.attributes.get("href") or "")[-12:]
        if not pid or not name:
            continue
        if pid in seen:
            continue
        brand_el = card.css_first("[data-testid='brand'], .brand")
        pack_el = card.css_first("[data-testid='unit'], .unit, .pack")
        price_el = card.css_first("[data-testid='price'], .selling-price, .price")
        mrp_el = card.css_first("[data-testid='mrp'], .mrp")
        item = ParsedListing(
            product_id=str(pid),
            sku_name=name,
            brand_name=_text(brand_el) or None,
            pack_raw=_text(pack_el) or None,
            selling_price=_to_float(_text(price_el)),
            mrp=_to_float(_text(mrp_el)),
            shelf_position=idx,
            search_query=query,
            in_stock="out of stock" not in card.text(separator=" ").lower(),
        )
        seen.add(item.product_id)
        listings.append(item)

    if not listings:
        raise ParseEmptyError("blinkit search returned zero product cards", html=html)
    return listings


def _normalize_card_text(text: str) -> str:
    text = (text or "").replace("\xa0", " ")
    text = re.sub(r"OFF(?=\d)", "OFF ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)(?=[A-Z₹])", " ", text)
    return " ".join(text.split())


def _listing_from_card(card, position: int, query: str) -> ParsedListing | None:
    pid = (card.attributes.get("id") or "").strip()
    raw = _normalize_card_text(card.text(separator=" ") or "")
    if not pid.isdigit() or not raw:
        return None
    lower = raw.lower()
    if "₹" not in raw and "rs" not in lower and "add" not in lower:
        return None
    prices = [float(x) for x in _PRICE.findall(raw)]
    selling = min(prices) if prices else None
    mrp = max(prices) if len(prices) > 1 else None
    pack = None
    pack_match = _PACK.search(raw)
    if pack_match:
        pack = pack_match.group(1)
    eta = None
    eta_match = _ETA.search(raw)
    if eta_match:
        eta = int(eta_match.group(1))
    name = _OFF.sub("", raw)
    name = _ETA.sub("", name)
    name = _PRICE.sub("", name)
    name = re.sub(r"\bADD\b", "", name, flags=re.I)
    if pack:
        name = re.sub(re.escape(pack), "", name, count=1, flags=re.I)
    name = " ".join(name.split()).strip(" -")
    if not name:
        return None
    in_stock = "out of stock" not in lower and "notify me" not in lower
    return ParsedListing(
        product_id=pid,
        variant_id=pid,
        sku_name=name,
        pack_raw=pack,
        mrp=mrp,
        selling_price=selling,
        in_stock=in_stock,
        shelf_position=position,
        organic_rank=position,
        delivery_promise_min=eta,
        delivery_time_text=f"{eta} mins" if eta else None,
        search_query=query,
    )


def _to_float(text: str) -> float | None:
    digits = re.sub(r"[^\d.]", "", text or "")
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def merchant_id_from_html(html: str) -> str | None:
    def _ok(value: str | None) -> str | None:
        if not value:
            return None
        text = str(value).strip()
        if not text.isdigit() or text in {"0", "00"}:
            return None
        return text

    state = _object_after(html, "window.grofers.PRELOADED_STATE")
    if state:
        data = state.get("data") if isinstance(state.get("data"), dict) else state
        merchant = data.get("merchant") if isinstance(data, dict) else None
        if isinstance(merchant, dict):
            got = _ok(str(merchant.get("id")) if merchant.get("id") is not None else None)
            if got:
                return got
        if isinstance(merchant, (int, str)):
            got = _ok(str(merchant))
            if got:
                return got
    patterns = [
        r'"merchant_id"\s*:\s*"?(\d+)"?',
        r'"merchantId"\s*:\s*"?(\d+)"?',
        r'"merchant":\{"id":(\d+)',
        r'data-merchant-id="(\d+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            got = _ok(m.group(1))
            if got:
                return got
    return None


def is_unserviceable(html: str) -> bool:
    lower = html.lower()
    return "not serviceable" in lower or "doesn't deliver" in lower or "does not deliver" in lower
