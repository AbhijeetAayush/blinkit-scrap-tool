from __future__ import annotations

import re
from urllib.parse import quote

from selectolax.parser import HTMLParser

from app.domain.errors import ParseEmptyError
from app.domain.models import Listing

_PRICE = re.compile(r"(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)")
_PACK = re.compile(r"(\d+(?:\.\d+)?\s?(?:kg|g|ml|l|pcs|pc|pack))\b", re.I)
_ETA = re.compile(r"(\d+)\s*mins?", re.I)
_OFF = re.compile(r"(\d+)\s*%\s*OFF", re.I)
_RATING = re.compile(r"\b([1-5](?:\.\d)?)\s*\(([\d.,]+\s*[kKmM]?)\)")
_COUNT_K = re.compile(r"^([\d.]+)\s*([kKmM])?$")
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


def parse_search_html(html: str, query: str = "") -> list[Listing]:
    seen: dict[str, Listing] = {}
    tree = HTMLParser(html)
    shelf_pos = 0
    organic_pos = 0
    for card in tree.css("div[role='button'][id]"):
        item = _listing_from_card(
            card,
            shelf_position=0,
            organic_rank=None,
            query=query,
        )
        if not item or item.product_id in seen:
            continue
        shelf_pos += 1
        item.shelf_position = shelf_pos
        if item.is_sponsored:
            item.organic_rank = None
        else:
            organic_pos += 1
            item.organic_rank = organic_pos
        seen[item.product_id] = item
    listings = list(seen.values())
    if not listings:
        raise ParseEmptyError("blinkit search returned zero product cards", html=html)
    return listings


def search_url(query: str) -> str:
    from app.platforms.blinkit import constants

    return constants.SEARCH_URL.format(query=quote(query))
