from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def observed_slot(now: datetime, slot_kind: str, tz: str = "Asia/Kolkata") -> datetime:
    zone = ZoneInfo(tz)
    local = now.astimezone(zone)
    day = local.date()

    if slot_kind == "morning":
        return datetime.combine(day, time(9, 0), tzinfo=zone)
    if slot_kind == "evening":
        return datetime.combine(day, time(19, 0), tzinfo=zone)
    if slot_kind == "resolve":
        return datetime.combine(day, time(6, 0), tzinfo=zone)
    if slot_kind == "manual":
        if local.time() < time(9, 0):
            return datetime.combine(day, time(9, 0), tzinfo=zone)
        if local.time() < time(19, 0):
            return datetime.combine(day, time(19, 0), tzinfo=zone)
        next_day = day + timedelta(days=1)
        return datetime.combine(next_day, time(9, 0), tzinfo=zone)

    hour = local.replace(minute=0, second=0, microsecond=0)
    return hour
