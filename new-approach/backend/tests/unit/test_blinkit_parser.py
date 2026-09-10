from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.errors import ParseEmptyError
from app.platforms.blinkit.parser import listing_from_dict, parse_search_html

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "blinkit" / "rendered_cards.html"


def test_parse_rendered_cards_extracts_priced_listings() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    listings = parse_search_html(html, query="mini mogra rice")
    assert len(listings) == 2

    by_id = {item.product_id: item for item in listings}
    kohinoor = by_id["527868"]
    assert kohinoor.selling_price == 502.0
    assert kohinoor.mrp == 700.0
    assert kohinoor.discount_percent == 28.0
    assert kohinoor.discount_text == "28% OFF"
    assert "Kohinoor" in (kohinoor.sku_name or "")
    assert kohinoor.pack_raw and "10" in kohinoor.pack_raw.lower()
    assert kohinoor.brand_name and "Kohinoor" in kohinoor.brand_name
    assert kohinoor.variant_id == "527868"
    assert kohinoor.shelf_position is not None
    assert kohinoor.product_url
    assert kohinoor.delivery_promise_min is not None or kohinoor.delivery_time_text is not None

    india_gate = by_id["100633"]
    assert india_gate.selling_price == 540.0
    assert india_gate.mrp == 720.0
    assert india_gate.search_query == "mini mogra rice"


def test_parse_empty_html_raises() -> None:
    with pytest.raises(ParseEmptyError):
        parse_search_html("<html><body><p>no products</p></body></html>", query="x")


def test_json_payload_fills_rating_and_category() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    payload = {
        "response": {
            "snippets": [
                {
                    "widget_type": "PRODUCT",
                    "data": {
                        "product_id": "527868",
                        "name": "Kohinoor Mini Mogra 2 Rice",
                        "rating": 4.2,
                        "rating_count": "12.3k",
                        "brand": "Kohinoor",
                        "l0_category": "Grocery & Kitchen",
                        "l1_category": "Atta, Rice & Dal",
                        "sub_category": "Rice",
                        "price": 502,
                        "mrp": 700,
                        "unit": "10 kg",
                        "is_ad": False,
                    },
                }
            ]
        }
    }
    listings = parse_search_html(html, query="mini mogra rice", json_payloads=[payload])
    kohinoor = {i.product_id: i for i in listings}["527868"]
    assert kohinoor.rating == 4.2
    assert kohinoor.rating_count == 12300
    assert kohinoor.category_path == ["Grocery & Kitchen", "Atta, Rice & Dal", "Rice"]
    assert kohinoor.selling_price == 502.0


def test_listing_from_dict_rating_v2() -> None:
    item = listing_from_dict(
        {
            "product_id": "1",
            "name": "Test Rice",
            "price": 100,
            "mrp": 120,
            "rating_v2": {"value": 4.5, "count_text": "1.2k"},
            "l0_category": "Staples",
        },
        1,
        "rice",
    )
    assert item is not None
    assert item.rating == 4.5
    assert item.rating_count == 1200
    assert item.category_path == ["Staples"]


def test_listing_from_dict_coerces_numeric_pack() -> None:
    item = listing_from_dict(
        {
            "product_id": "99",
            "name": "Test Pack",
            "price": 10,
            "mrp": 12,
            "unit": 1,
            "rating": 4.1,
            "rating_count": 10,
            "l0_category": "Staples",
        },
        1,
        "test",
    )
    assert item is not None
    assert item.pack_raw == "1"
    assert item.rating == 4.1
    assert item.category_path == ["Staples"]
