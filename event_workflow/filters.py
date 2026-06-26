from __future__ import annotations

import re
from datetime import date

from event_workflow.dates import MAX_EVENT_SPAN_DAYS
from event_workflow.models import EventRecord


def filter_by_sources(events: list[EventRecord], sources: set[str] | None) -> list[EventRecord]:
    if not sources:
        return events
    normalized = {source.lower() for source in sources}
    return [event for event in events if event.source.lower() in normalized]


def filter_by_keywords(events: list[EventRecord], keywords: list[str]) -> list[EventRecord]:
    if not keywords:
        return events
    lowered = [keyword.lower() for keyword in keywords]
    results: list[EventRecord] = []
    for event in events:
        haystack = " ".join(
            filter(
                None,
                [event.title, event.description, event.location, " ".join(event.categories)],
            )
        ).lower()
        if any(keyword in haystack for keyword in lowered):
            results.append(event)
    return results


def filter_online_only(events: list[EventRecord]) -> list[EventRecord]:
    return [event for event in events if _is_online(event.location)]


def filter_in_person_only(events: list[EventRecord]) -> list[EventRecord]:
    return [event for event in events if event.location and not _is_online(event.location)]


def filter_by_date_window(
    events: list[EventRecord],
    window_start: date,
    window_end: date,
) -> list[EventRecord]:
    return [event for event in events if event.overlaps_window(window_start, window_end)]


def filter_exclude_cancelled(events: list[EventRecord]) -> list[EventRecord]:
    return [event for event in events if not re.search(r"cancel+ed", event.title, re.IGNORECASE)]


def event_duration_days(event: EventRecord) -> int | None:
    if event.start_at is None and event.end_at is None:
        return None
    event_start = (event.start_at or event.end_at).date()
    event_end = (event.end_at or event.start_at).date()
    return (event_end - event_start).days


def filter_exclude_long_span(
    events: list[EventRecord],
    max_days: int = MAX_EVENT_SPAN_DAYS,
) -> list[EventRecord]:
    """Drop reminders/deadlines whose start–end span exceeds *max_days*."""
    kept: list[EventRecord] = []
    for event in events:
        duration = event_duration_days(event)
        if duration is not None and duration > max_days:
            continue
        kept.append(event)
    return kept


def _is_online(location: str | None) -> bool:
    if not location:
        return False
    normalized = location.lower()
    return "online" in normalized or normalized.startswith("http")
