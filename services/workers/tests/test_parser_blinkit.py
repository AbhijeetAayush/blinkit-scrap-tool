from pathlib import Path

import pytest

from src.domain.errors import ParseEmptyError
from src.platforms.blinkit.parser import parse_search_html

FIXTURE = Path(__file__).parent / "fixtures" / "blinkit" / "search_sample.html"


def test_parser_two_cards_from_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    listings = parse_search_html(html, query="milk 500")
    assert len(listings) == 2
    ids = {item.product_id for item in listings}
    assert ids == {"1001", "1002"}
    names = {item.sku_name for item in listings}
    assert any("Amul" in n for n in names)
    assert any("Nandini" in n for n in names)


def test_parser_rendered_role_button_cards():
    html = (Path(__file__).parent / "fixtures" / "blinkit" / "rendered_cards.html").read_text(encoding="utf-8")
    listings = parse_search_html(html, query="kohinoor mini mogra 2")
    by_id = {item.product_id: item for item in listings}
    assert "527868" in by_id
    assert "100633" in by_id
    kohinoor = by_id["527868"]
    assert "Kohinoor" in kohinoor.sku_name
    assert kohinoor.brand_name == "Kohinoor"
    assert kohinoor.selling_price == 502
    assert kohinoor.mrp == 700
    assert kohinoor.discount_percent == 28
    assert kohinoor.discount_text and "28" in kohinoor.discount_text
    assert kohinoor.pack_raw and "10" in kohinoor.pack_raw
    assert kohinoor.in_stock is True
    india = by_id["100633"]
    assert india.brand_name == "India Gate"


def test_merchant_id_from_preloaded_state():
    from src.platforms.blinkit.parser import merchant_id_from_html

    html = 'window.grofers.PRELOADED_STATE = {"data":{"merchant":{"id":30377},"location":{"coords":{"lat":12.9}}}};'
    assert merchant_id_from_html(html) == "30377"


def test_empty_parse_raises_and_does_not_invent_oos():
    with pytest.raises(ParseEmptyError):
        parse_search_html("<html><body><p>no products</p></body></html>", query="milk")
