from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.errors import ParseEmptyError
from app.platforms.blinkit.parser import parse_search_html

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
