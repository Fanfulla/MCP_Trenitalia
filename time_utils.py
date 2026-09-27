"""Railway dates are always interpreted in Europe/Rome."""

from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def now_rome() -> datetime:
    return datetime.now(ROME)


def format_viaggiatreno_time(value: datetime | None = None) -> str:
    current = (value or now_rome()).astimezone(ROME)
    text = (f"{_DAYS[current.weekday()]} {_MONTHS[current.month - 1]} "
            f"{current.day:02d} {current.year} {current:%H:%M:%S} GMT{current:%z}")
    return quote(text, safe="")


def timestamp_to_iso(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    try:
        millis = float(value)
        if millis <= 0:
            return None
        return datetime.fromtimestamp(millis / 1000, ROME).isoformat(timespec="seconds")
    except (TypeError, ValueError, OverflowError, OSError):
        return None
