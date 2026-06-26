from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

DEFAULT_HORIZON_DAYS = 7
MAX_EVENT_SPAN_DAYS = 14

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def scan_window(reference: date | None = None, horizon_days: int = DEFAULT_HORIZON_DAYS) -> tuple[date, date]:
    """Return inclusive [start, end] spanning *horizon_days* calendar days including today."""
    start = reference or date.today()
    end = start + timedelta(days=horizon_days - 1)
    return start, end


def parse_mcgill_date_text(text: str) -> tuple[datetime | None, datetime | None]:
    """Parse McGill listing date strings such as 'Thursday, June 18, 2026 07:30 to 08:30'."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return None, None

    parts = re.split(r"\s+to\s+", cleaned, maxsplit=1)
    start = _parse_mcgill_fragment(parts[0])
    end = _parse_mcgill_fragment(parts[1], default=start) if len(parts) > 1 else None

    if start and end and end < start:
        end = end.replace(year=start.year, month=start.month, day=start.day)
        if end < start:
            end = start

    return start, end or start


def _parse_mcgill_fragment(fragment: str, *, default: datetime | None = None) -> datetime | None:
    fragment = fragment.strip()
    match = re.search(
        r"(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})"
        r"(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{2}))?",
        fragment,
    )
    if match:
        month_name = match.group("month").lower()
        month = MONTHS.get(month_name)
        if month is None:
            return None

        day = int(match.group("day"))
        year = int(match.group("year"))
        hour = int(match.group("hour")) if match.group("hour") else 0
        minute = int(match.group("minute")) if match.group("minute") else 0
        return datetime(year, month, day, hour, minute)

    if default is not None:
        time_match = re.search(r"(?P<hour>\d{1,2}):(?P<minute>\d{2})", fragment)
        if time_match:
            hour = int(time_match.group("hour"))
            minute = int(time_match.group("minute"))
            return default.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return None


def parse_concordia_when(text: str) -> tuple[datetime | None, datetime | None]:
    """Parse Concordia 'When' field, e.g. 'June 18, 2026, 8 a.m. – 10 a.m.'."""
    cleaned = re.sub(r"\s+", " ", text.strip().replace("\u2013", "-").replace("\u2014", "-"))
    if not cleaned:
        return None, None

    range_match = re.match(
        r"(?P<start_month>[A-Za-z]+)\s+(?P<start_day>\d{1,2}),?\s+(?P<start_year>\d{4})"
        r"(?:\s*-\s*(?P<end_month>[A-Za-z]+)\s+(?P<end_day>\d{1,2}),?\s+(?P<end_year>\d{4}))?"
        r",?\s*(?P<start_time>.+?)(?:\s*-\s*(?P<end_time>.+))?$",
        cleaned,
    )
    if not range_match:
        return None, None

    start_month = MONTHS.get(range_match.group("start_month").lower())
    if start_month is None:
        return None, None

    start_day = int(range_match.group("start_day"))
    start_year = int(range_match.group("start_year"))
    start_time = _parse_concordia_clock(range_match.group("start_time"))

    end_month = start_month
    end_day = start_day
    end_year = start_year
    if range_match.group("end_month"):
        end_month = MONTHS.get(range_match.group("end_month").lower(), start_month)
        end_day = int(range_match.group("end_day"))
        end_year = int(range_match.group("end_year"))

    end_time = _parse_concordia_clock(range_match.group("end_time")) if range_match.group("end_time") else start_time

    start_at = datetime.combine(date(start_year, start_month, start_day), start_time or time.min)
    end_at = datetime.combine(date(end_year, end_month, end_day), end_time or time.max.replace(microsecond=0))
    return start_at, end_at


def _parse_concordia_clock(value: str | None) -> time | None:
    if not value:
        return None
    value = value.strip().lower().replace(".", "")
    match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", value)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if "p" in meridiem and hour != 12:
        hour += 12
    if "a" in meridiem and hour == 12:
        hour = 0
    return time(hour, minute)
