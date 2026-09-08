from uuid import uuid4

from src.domain.models import ParsedListing, Sku
from src.match.cascade import match_listing


def _sku(**kwargs) -> Sku:
    defaults = dict(
        id=uuid4(),
        brand_id=uuid4(),
        sku_role="self",
        display_name="Gold Milk 500ml",
        search_query="milk 500",
        brand_name="Amul",
        pack_raw="500 ml",
        pack_ml=500,
    )
    defaults.update(kwargs)
    return Sku(**defaults)


def test_pack_conflict_500_vs_1000_skips_exact():
    sku = _sku(pack_ml=500, pack_raw="500 ml")
    listing = ParsedListing(
        product_id="x",
        sku_name="Gold Milk 1L",
        brand_name="Amul",
        pack_raw="1L",
    )
    result = match_listing(listing, [sku])
    assert result.relation == "unmatched"
    assert result.sku_id is None


def test_name_overlap_matches_when_card_omits_brand():
    sku = _sku(
        display_name="Kohinoor Mini Mogra 2 Rice 5 kg",
        search_query="kohinoor mini mogra 2",
        brand_name="Kohinoor",
        pack_raw="5 kg",
        pack_ml=None,
    )
    listing = ParsedListing(
        product_id="527868",
        sku_name="Kohinoor Mini Mogra 2 Rice",
        brand_name=None,
        pack_raw="10 kg",
        selling_price=502,
    )
    result = match_listing(listing, [sku], auto_commit=0.95)
    assert result.sku_id == sku.id
    assert result.relation in {"exact", "like_item"}
    assert result.confidence >= 0.8


def test_india_gate_inferred_brand_from_title():
    sku = _sku(
        sku_role="brand_competitor",
        display_name="India Gate Mini Mogra Rice 10 kg",
        search_query="india gate mini mogra",
        brand_name="India Gate",
        pack_raw="10 kg",
        pack_ml=None,
    )
    listing = ParsedListing(
        product_id="402268",
        sku_name="India Gate Mogra Lite /Mini Mogra Basmati Rice (Short Grain)",
        brand_name=None,
        pack_raw="10 kg",
        selling_price=512,
    )
    result = match_listing(listing, [sku], auto_commit=0.95)
    assert result.sku_id == sku.id
    assert result.confidence >= 0.8
