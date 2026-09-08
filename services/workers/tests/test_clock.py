from datetime import datetime
from zoneinfo import ZoneInfo

from src.app.clock import observed_slot

IST = ZoneInfo("Asia/Kolkata")


def test_morning_slot_is_0900_ist_that_calendar_day():
    now = datetime(2026, 9, 7, 10, 15, tzinfo=IST)
    slot = observed_slot(now, "morning")
    assert slot == datetime(2026, 9, 7, 9, 0, tzinfo=IST)


def test_evening_slot_is_1900_ist():
    now = datetime(2026, 9, 7, 20, 0, tzinfo=IST)
    slot = observed_slot(now, "evening")
    assert slot == datetime(2026, 9, 7, 19, 0, tzinfo=IST)


def test_resolve_slot_is_0600_ist():
    now = datetime(2026, 9, 7, 6, 5, tzinfo=IST)
    slot = observed_slot(now, "resolve")
    assert slot == datetime(2026, 9, 7, 6, 0, tzinfo=IST)


def test_manual_before_nine_uses_today_morning():
    now = datetime(2026, 9, 7, 8, 0, tzinfo=IST)
    slot = observed_slot(now, "manual")
    assert slot == datetime(2026, 9, 7, 9, 0, tzinfo=IST)


def test_manual_before_nineteen_uses_today_evening():
    now = datetime(2026, 9, 7, 12, 0, tzinfo=IST)
    slot = observed_slot(now, "manual")
    assert slot == datetime(2026, 9, 7, 19, 0, tzinfo=IST)


def test_manual_after_nineteen_uses_next_morning():
    now = datetime(2026, 9, 7, 20, 0, tzinfo=IST)
    slot = observed_slot(now, "manual")
    assert slot == datetime(2026, 9, 8, 9, 0, tzinfo=IST)
