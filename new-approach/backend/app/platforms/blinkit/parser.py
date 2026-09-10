from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from selectolax.parser import HTMLParser

from app.domain.errors import ParseEmptyError
from app.domain.models import Listing

_PRICE = re.compile(r"(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)")
_PACK = re.compile(r"(\d+(?:\.\d+)?\s?(?:kg|g|ml|l|pcs|pc|pack))\b", re.I)
_ETA = re.compile(r"(\d+)\s*mins?", re.I)
_OFF = re.compile(r"(\d+)\s*%\s*OFF", re.I)
_RATING = re.compile(
    r"\b([1-5](?:\.\d)?)\s*(?:★|⭐)?\s*[\(\[]?\s*([\d.,]+\s*[kKmM]?)\s*[\)\]]?",
)
_COUNT_K = re.compile(r"^([\d.]+)\s*([kKmM])?$")
_JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_CDN = "cdn.grofers.com"

_KNOWN_BRANDS = tuple(
    sorted(
        {
            "india gate",
            "kohinoor",
            "daawat",
            "dawat",
            "fortune",
            "lal qilla",
            "tilda",
            "aashirvaad",
            "patanjali",
            "saffola",
            "dhara",
            "engine",
            "bb royal",
            "organic tattva",
        },
        key=len,
        reverse=True,
    )
)
_PRODUCT_WORDS = {
    "rice",
    "oil",
    "atta",
    "flour",
    "milk",
    "ghee",
    "sugar",
    "dal",
    "wheat",
    "basmati",
    "mogra",
    "sona",
    "masoori",
    "masuri",
}


def infer_brand_name(name: str | None) -> str | None:
    if not name:
        return None
    lower = name.lower()
    for brand in _KNOWN_BRANDS:
        if lower.startswith(brand) or f" {brand} " in f" {lower} ":
            return " ".join(w.capitalize() for w in brand.split())
    tokens = [t for t in re.split(r"\s+", name.strip()) if t]
    kept: list[str] = []
    for token in tokens:
        if token.lower() in _PRODUCT_WORDS:
            break
        if not re.match(r"^[A-Za-z][A-Za-z.&'-]*$", token):
            break
        kept.append(token)
        if len(kept) >= 3:
            break
    return " ".join(kept) if kept else None


def _parse_count(raw: str) -> int | None:
    m = _COUNT_K.match(raw.replace(",", "").strip())
    if not m:
        return None
    n = float(m.group(1))
    suffix = (m.group(2) or "").lower()
    if suffix == "k":
        n *= 1000
    elif suffix == "m":
        n *= 1_000_000
    return int(round(n))


def _normalize_card_text(text: str) -> str:
    text = (text or "").replace("\xa0", " ")
    text = re.sub(r"OFF(?=\d)", "OFF ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)(?=[A-Z₹])", " ", text)
    return " ".join(text.split())


def _urls_from_attr(value: str | None) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for part in value.split(","):
        url = part.strip().split(" ")[0].strip()
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("data:"):
            continue
        if _CDN in url and url.startswith("http"):
            out.append(url)
        elif url.startswith("http") and "grofers" in url:
            out.append(url)
    return out


def _card_image_url(card) -> str | None:
    ranked: list[tuple[int, str]] = []
    for img in card.css("img"):
        classes = f"{img.attributes.get('class') or ''} {img.attributes.get('style') or ''}"
        placeholder = "opacity-0" in classes
        candidates: list[str] = []
        for attr in ("src", "data-src", "srcset", "data-srcset"):
            candidates.extend(_urls_from_attr(img.attributes.get(attr)))
        for url in candidates:
            ranked.append((1 if placeholder else 0, url))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][1]


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


def _rating_fields(raw: dict) -> tuple[float | None, int | None]:
    rating = raw.get("rating")
    count = (
        raw.get("rating_count")
        or raw.get("ratingCount")
        or raw.get("number_of_ratings")
        or raw.get("ratings_count")
    )
    if isinstance(rating, dict):
        count = (
            count
            if count is not None
            else (
                rating.get("count")
                or rating.get("rating_count")
                or rating.get("count_text")
                or rating.get("countText")
            )
        )
        rating = rating.get("value") or rating.get("average") or rating.get("avg") or rating.get("rating")
    rating_v2 = raw.get("rating_v2") or raw.get("ratingV2")
    if isinstance(rating_v2, dict):
        if rating is None:
            rating = rating_v2.get("value") or rating_v2.get("rating")
        if count is None:
            count = rating_v2.get("count") or rating_v2.get("count_text")
    parsed_rating = None
    if rating is not None and not isinstance(rating, dict):
        try:
            parsed_rating = float(str(rating).strip())
        except ValueError:
            parsed_rating = None
    parsed_count = None
    if isinstance(count, bool):
        parsed_count = None
    elif isinstance(count, int):
        parsed_count = count
    elif isinstance(count, float):
        parsed_count = int(round(count))
    elif isinstance(count, str):
        parsed_count = _parse_count(count)
    return parsed_rating, parsed_count


def _category_path(raw: dict) -> list[str]:
    junk = {"", "-", "na", "n/a", "#-na", "null", "none", "undefined"}
    path: list[str] = []

    def _push(val: Any) -> None:
        if isinstance(val, dict):
            val = val.get("name") or val.get("title") or val.get("text")
        if not isinstance(val, str):
            return
        text = val.strip()
        if not text or text.lower() in junk or text in path:
            return
        path.append(text)

    for key in (
        "l0_category",
        "l1_category",
        "l2_category",
        "sub_category",
        "category",
        "primary_category",
        "secondary_category",
        "category_name",
        "type",
        "product_type",
    ):
        _push(raw.get(key))
    nested = raw.get("categories") or raw.get("category_path")
    if isinstance(nested, list):
        for item in nested:
            _push(item)
    return path


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _walk_products(obj: Any, acc: list[dict]) -> None:
    if isinstance(obj, dict):
        if "product_id" in obj or "productId" in obj or (
            "name" in obj and ("price" in obj or "mrp" in obj or "selling_price" in obj)
        ):
            acc.append(obj)
        data = obj.get("data")
        if isinstance(data, dict) and (
            "product_id" in data or "productId" in data or ("name" in data and ("price" in data or "mrp" in data))
        ):
            acc.append(data)
        for value in obj.values():
            _walk_products(value, acc)
    elif isinstance(obj, list):
        for item in obj:
            _walk_products(item, acc)


def _as_str(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def listing_from_dict(raw: dict, position: int, query: str) -> Listing | None:
    product_id = str(raw.get("product_id") or raw.get("productId") or "")
    name = raw.get("name") or raw.get("title") or raw.get("sku_name")
    if isinstance(name, dict):
        name = name.get("text") or name.get("value")
    if not name:
        name = raw.get("display_name") or raw.get("product_name")
    rating, rating_count = _rating_fields(raw)
    if not product_id:
        return None
    if not isinstance(name, str) or not name:
        if rating is None and rating_count is None:
            return None
        name = f"product {product_id}"
    price = raw.get("price") or raw.get("selling_price") or raw.get("offer_price")
    mrp = raw.get("mrp")
    in_stock = raw.get("in_stock")
    if in_stock is None:
        in_stock = not bool(raw.get("out_of_stock") or raw.get("is_sold_out"))
    discount_raw = raw.get("discount") or raw.get("discount_text") or raw.get("offer_text")
    discount_text = _as_str(discount_raw)
    off = None
    if discount_text:
        off_m = _OFF.search(discount_text)
        if off_m:
            off = float(off_m.group(1))
    if off is None and isinstance(raw.get("discount_percent"), (int, float)):
        off = float(raw["discount_percent"])
    brand = raw.get("brand") or raw.get("brand_name")
    if isinstance(brand, dict):
        brand = brand.get("name") or brand.get("title")
    brand_s = _as_str(brand)
    inventory = raw.get("inventory") or raw.get("inventory_shown")
    if isinstance(inventory, dict):
        inventory = inventory.get("count") or inventory.get("value")
    qty = raw.get("max_qty") if raw.get("max_qty") is not None else raw.get("max_allowed_quantity")
    images = raw.get("images") or raw.get("image_list") or []
    image_url = raw.get("image_url")
    if not image_url and isinstance(images, list) and images:
        first = images[0]
        image_url = first if isinstance(first, str) else (first.get("url") if isinstance(first, dict) else None)
    eta = raw.get("eta_minutes")
    delivery_time = raw.get("delivery_time") or raw.get("eta_text")
    if delivery_time is None and eta is not None:
        delivery_time = f"{eta} mins"
    pack_raw = _as_str(raw.get("unit") or raw.get("quantity") or raw.get("pack"))
    product_url = _as_str(raw.get("product_url") or raw.get("deeplink")) or f"https://blinkit.com/prn/prid/{product_id}"
    try:
        return Listing(
            product_id=product_id,
            variant_id=str(raw.get("variant_id") or raw.get("variantId") or product_id),
            group_id=_as_str(raw.get("group_id")),
            sku_name=str(name),
            brand_name=brand_s or infer_brand_name(str(name)),
            pack_raw=pack_raw,
            mrp=_to_float(mrp),
            selling_price=_to_float(price),
            in_stock=bool(in_stock),
            inventory_shown=int(inventory) if inventory is not None and not isinstance(inventory, dict) else None,
            qty_cap=int(qty) if qty is not None and not isinstance(qty, dict) else None,
            is_sponsored=raw.get("is_ad") if raw.get("is_ad") is not None else raw.get("is_sponsored"),
            shelf_position=int(raw.get("position") or position),
            organic_rank=int(raw["organic_rank"]) if raw.get("organic_rank") is not None else None,
            rating=rating,
            rating_count=rating_count,
            image_url=image_url if isinstance(image_url, str) else None,
            product_url=product_url,
            offer_text=_as_str(raw.get("offer_text")) or discount_text,
            discount_text=discount_text,
            discount_percent=off,
            delivery_promise_min=int(eta) if eta is not None else None,
            delivery_time_text=_as_str(delivery_time),
            category_path=_category_path(raw),
            search_query=query,
            result_page=1,
        )
    except Exception:
        return None


def merge_listing(base: Listing, extra: Listing) -> Listing:
    data = base.model_dump()
    for key, value in extra.model_dump().items():
        cur = data.get(key)
        if key == "category_path" and isinstance(cur, list) and isinstance(value, list):
            merged = list(cur)
            for item in value:
                if item not in merged:
                    merged.append(item)
            data[key] = merged
            continue
        if cur in (None, "", [], False) and value not in (None, "", [], False):
            data[key] = value
        elif key in {
            "brand_name",
            "discount_text",
            "discount_percent",
            "rating",
            "rating_count",
            "image_url",
            "product_url",
            "is_sponsored",
            "pack_raw",
            "inventory_shown",
            "qty_cap",
            "group_id",
            "offer_text",
            "delivery_promise_min",
            "delivery_time_text",
        }:
            if cur in (None, "", []) and value not in (None, "", []):
                data[key] = value
    return Listing(**data)


def _listing_from_card(
    card,
    *,
    shelf_position: int,
    organic_rank: int | None,
    query: str,
) -> Listing | None:
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
    off_m = _OFF.search(raw)
    discount_text = f"{off_m.group(1)}% OFF" if off_m else None
    discount_pct = float(off_m.group(1)) if off_m else None
    rating = None
    rating_count = None
    rating_m = _RATING.search(raw)
    if rating_m:
        rating = float(rating_m.group(1))
        rating_count = _parse_count(rating_m.group(2))
    name = _OFF.sub("", raw)
    name = _ETA.sub("", name)
    name = _PRICE.sub("", name)
    name = _RATING.sub("", name)
    name = re.sub(r"\bADD\b", "", name, flags=re.I)
    name = re.sub(r"\bAD\b", "", name, flags=re.I)
    name = re.sub(r"[★⭐]", "", name)
    if pack:
        name = re.sub(re.escape(pack), "", name, count=1, flags=re.I)
    name = " ".join(name.split()).strip(" -")
    if not name:
        return None
    in_stock = "out of stock" not in lower and "notify me" not in lower
    card_html = (getattr(card, "html", None) or "").lower()
    sponsored = "ad_without_bg" in card_html
    if lower.startswith("sponsored") or " sponsored " in f" {lower} ":
        sponsored = True
    href = card.attributes.get("href")
    product_url = href if href and href.startswith("http") else f"https://blinkit.com/prn/prid/{pid}"
    return Listing(
        product_id=pid,
        variant_id=pid,
        sku_name=name,
        brand_name=infer_brand_name(name),
        pack_raw=pack,
        mrp=mrp,
        selling_price=selling,
        in_stock=in_stock,
        is_sponsored=True if sponsored else None,
        shelf_position=shelf_position,
        organic_rank=organic_rank,
        rating=rating,
        rating_count=rating_count,
        image_url=_card_image_url(card),
        product_url=product_url,
        discount_percent=discount_pct,
        discount_text=discount_text,
        offer_text=discount_text,
        delivery_promise_min=eta,
        delivery_time_text=f"{eta} mins" if eta else None,
        search_query=query,
        result_page=1,
    )


def listings_from_payloads(payloads: list[Any], query: str = "") -> list[Listing]:
    seen: dict[str, Listing] = {}
    for payload in payloads:
        blob: list[dict] = []
        _walk_products(payload, blob)
        for raw in blob:
            item = listing_from_dict(raw, len(seen) + 1, query)
            if not item:
                continue
            existing = seen.get(item.product_id)
            if existing:
                seen[item.product_id] = merge_listing(existing, item)
            else:
                seen[item.product_id] = item
    return list(seen.values())


def parse_search_html(
    html: str,
    query: str = "",
    *,
    json_payloads: list[Any] | None = None,
) -> list[Listing]:
    seen: dict[str, Listing] = {}

    def _add(item: Listing | None) -> None:
        if not item:
            return
        existing = seen.get(item.product_id)
        if existing:
            seen[item.product_id] = merge_listing(existing, item)
            return
        seen[item.product_id] = item

    for match in _JSON_LD.finditer(html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        blob: list[dict] = []
        _walk_products(data, blob)
        for raw in blob:
            _add(listing_from_dict(raw, len(seen) + 1, query))

    for marker in ("window.grofers.PRELOADED_STATE", "window.__PRELOADED_STATE__"):
        state = _object_after(html, marker)
        if not state:
            continue
        blob = []
        _walk_products(state, blob)
        for raw in blob:
            _add(listing_from_dict(raw, len(seen) + 1, query))

    for item in listings_from_payloads(json_payloads or [], query=query):
        _add(item)

    tree = HTMLParser(html)
    shelf_pos = 0
    organic_pos = 0
    for card in tree.css("div[role='button'][id]"):
        provisional = _listing_from_card(
            card,
            shelf_position=0,
            organic_rank=None,
            query=query,
        )
        if not provisional:
            continue
        # always merge HTML for price/rank; create if new
        if provisional.product_id not in seen:
            shelf_pos += 1
            provisional.shelf_position = shelf_pos
            if provisional.is_sponsored:
                provisional.organic_rank = None
            else:
                organic_pos += 1
                provisional.organic_rank = organic_pos
            seen[provisional.product_id] = provisional
        else:
            shelf_pos += 1
            provisional.shelf_position = shelf_pos
            if provisional.is_sponsored:
                provisional.organic_rank = None
            else:
                organic_pos += 1
                provisional.organic_rank = organic_pos
            seen[provisional.product_id] = merge_listing(seen[provisional.product_id], provisional)

    listings = list(seen.values())
    listings.sort(key=lambda x: (x.shelf_position is None, x.shelf_position or 10_000))
    if not listings:
        raise ParseEmptyError("blinkit search returned zero product cards", html=html)
    return listings


def search_url(query: str) -> str:
    from app.platforms.blinkit import constants

    return constants.SEARCH_URL.format(query=quote(query))
