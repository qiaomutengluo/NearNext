from __future__ import annotations

from datetime import date, datetime

from event_workflow.filters import (
    filter_by_keywords,
    filter_by_sources,
    filter_exclude_cancelled,
    filter_in_person_only,
    filter_online_only,
)
from event_workflow.models import EventRecord


def _event(
    *,
    title: str,
    source: str = "mcgill",
    location: str | None = "Online",
    description: str | None = None,
) -> EventRecord:
    return EventRecord(
        source=source,
        title=title,
        start_at=datetime(2026, 6, 18, 9, 0),
        end_at=datetime(2026, 6, 18, 10, 0),
        location=location,
        description=description,
        url=None,
    )


def test_filter_by_sources() -> None:
    events = [_event(title="A", source="mcgill"), _event(title="B", source="concordia")]
    filtered = filter_by_sources(events, {"mcgill"})
    assert len(filtered) == 1
    assert filtered[0].source == "mcgill"


def test_filter_by_keywords_matches_title_or_description() -> None:
    events = [
        _event(title="Python workshop", description="coding"),
        _event(title="Music night", description="jazz"),
    ]
    filtered = filter_by_keywords(events, ["python"])
    assert len(filtered) == 1
    assert filtered[0].title == "Python workshop"


def test_filter_online_and_in_person() -> None:
    events = [
        _event(title="Online talk", location="Online"),
        _event(title="Campus tour", location="SGW campus LB-187"),
    ]
    assert len(filter_online_only(events)) == 1
    assert len(filter_in_person_only(events)) == 1


def test_filter_exclude_cancelled() -> None:
    events = [
        _event(title="Active event"),
        _event(title="Contemplative Walk: Joy! – Cancelled"),
    ]
    filtered = filter_exclude_cancelled(events)
    assert len(filtered) == 1
    assert "Cancelled" not in filtered[0].title


def test_overlaps_window() -> None:
    event = EventRecord(
        source="mcgill",
        title="Range",
        start_at=datetime(2026, 6, 15, 0, 0),
        end_at=datetime(2026, 6, 18, 0, 0),
        location=None,
        description=None,
        url=None,
    )
    assert event.overlaps_window(date(2026, 6, 18), date(2026, 6, 21))
    assert not event.overlaps_window(date(2026, 6, 19), date(2026, 6, 21))
