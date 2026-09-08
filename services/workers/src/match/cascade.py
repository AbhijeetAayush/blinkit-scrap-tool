from __future__ import annotations

from rapidfuzz import fuzz

from src.domain.models import MatchResult, ParsedListing, Sku
from src.normalize.brand import normalize_brand
from src.normalize.pack import parse_pack, packs_compatible


def _tokens(text: str) -> set[str]:
    return {t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t}


def _token_overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _name_score(a: str, b: str) -> float:
    return max(_token_overlap(a, b), fuzz.token_set_ratio(a or "", b or "") / 100.0)


def _pack_size(sku: Sku | None = None, listing: ParsedListing | None = None) -> int | None:
    if sku is not None:
        if sku.pack_ml:
            return sku.pack_ml
        parsed = parse_pack(sku.pack_raw)
        return parsed.pack_ml or parsed.pack_g
    if listing is not None:
        parsed = parse_pack(listing.pack_raw)
        return parsed.pack_ml or parsed.pack_g
    return None


def _listing_brand(listing: ParsedListing, skus: list[Sku]) -> str:
    direct = normalize_brand(listing.brand_name)
    if direct:
        return direct
    name = (listing.sku_name or "").lower()
    brands = sorted({normalize_brand(s.brand_name) for s in skus if s.brand_name}, key=len, reverse=True)
    for brand in brands:
        if brand and brand in name:
            return brand
    return ""


def match_listing(
    listing: ParsedListing,
    skus: list[Sku],
    *,
    auto_commit: float = 0.95,
) -> MatchResult:
    listing_size = _pack_size(listing=listing)
    listing_brand = _listing_brand(listing, skus)

    for sku in skus:
        if sku.blinkit_product_id and sku.blinkit_product_id == listing.product_id:
            return MatchResult(
                sku_id=sku.id,
                relation="exact",
                confidence=1.0,
                method="product_id",
                sku_role=sku.sku_role,
            )

    best: MatchResult | None = None
    for sku in skus:
        sku_size = _pack_size(sku=sku)
        score = _name_score(listing.sku_name, sku.display_name)
        pack_mismatch = bool(
            listing_size and sku_size and not packs_compatible(listing_size, sku_size)
        )
        # Hard skip clear pack conflicts unless the title is nearly identical (same line, other size).
        if pack_mismatch and score < 0.9:
            continue
        pack_ok = not pack_mismatch
        brand_ok = bool(listing_brand) and listing_brand == normalize_brand(sku.brand_name)

        if brand_ok and pack_ok and score >= 0.5:
            cand = MatchResult(
                sku_id=sku.id,
                relation="exact",
                confidence=0.95,
                method="brand_pack",
                sku_role=sku.sku_role,
            )
            if best is None or cand.confidence > best.confidence:
                best = cand
            continue

        if brand_ok and score >= 0.55:
            cand = MatchResult(
                sku_id=sku.id,
                relation="exact" if pack_ok else "like_item",
                confidence=0.92 if pack_ok else 0.86,
                method="brand_name",
                sku_role=sku.sku_role,
            )
            if best is None or cand.confidence > best.confidence:
                best = cand
            continue

        if score >= 0.78:
            cand = MatchResult(
                sku_id=sku.id,
                relation="exact" if pack_ok else "like_item",
                confidence=0.9 if pack_ok else 0.84,
                method="name_overlap",
                sku_role=sku.sku_role,
            )
            if best is None or cand.confidence > best.confidence:
                best = cand
            continue

        if sku.sku_role == "brand_competitor" and brand_ok and score >= 0.5:
            cand = MatchResult(
                sku_id=sku.id,
                relation="like_item",
                confidence=0.88 if pack_ok else 0.82,
                method="competitor_name",
                sku_role=sku.sku_role,
            )
            if best is None or cand.confidence > best.confidence:
                best = cand

    if best:
        return best
    return MatchResult(sku_id=None, relation="unmatched", confidence=0.0, method="none", sku_role=None)


def listing_tracked(listing: ParsedListing, skus: list[Sku], result: MatchResult) -> bool:
    return bool(result.sku_id and result.relation in {"exact", "like_item"})
