import json
from pathlib import Path

from src.platforms.blinkit.enrich import enrich_listings
from src.platforms.blinkit.layout import listings_from_layout_payload
from src.platforms.blinkit.parser import parse_search_html

FIXTURE = Path(__file__).parent / "fixtures" / "blinkit" / "product_layout_527868.json"


def test_enrich_json_rating_does_not_overwrite_html_price():
    html = (
        '<div role="button" id="527868">28% OFF8 minsKohinoor Mini Mogra 2 Rice10 kg₹502 ₹700ADD</div>'
    )
    html_listings = parse_search_html(html, query="kohinoor")
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    extras = listings_from_layout_payload(payload, "kohinoor")
    merged = enrich_listings(html_listings, extras)
    kohinoor = next(item for item in merged if item.product_id == "527868")
    assert kohinoor.selling_price == 502
    assert kohinoor.mrp == 700
    assert kohinoor.discount_percent == 28
    assert kohinoor.rating == 4.2
    assert kohinoor.rating_count == 12345
    assert kohinoor.inventory_shown == 12


def test_enrich_without_json_keeps_html():
    html = (
        '<div role="button" id="527868">28% OFF8 minsKohinoor Mini Mogra 2 Rice10 kg₹502 ₹700ADD</div>'
    )
    html_listings = parse_search_html(html, query="kohinoor")
    merged = enrich_listings(html_listings, [])
    assert merged[0].selling_price == 502
    assert merged[0].rating is None


def test_listings_from_layout_fixture():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    extras = listings_from_layout_payload(payload, "")
    assert extras[0].product_id == "527868"
    assert extras[0].rating == 4.2
    assert extras[0].rating_count == 12345
