from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from event_workflow.dates import parse_concordia_when, parse_mcgill_date_text, scan_window
from event_workflow.sources.concordia import ConcordiaEventSource
from event_workflow.sources.mcgill import McGillEventSource

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mcgill_html() -> str:
    return (FIXTURES / "mcgill_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def concordia_html() -> str:
    return (FIXTURES / "concordia_sample.html").read_text(encoding="utf-8")


class TestDateParsing:
    def test_scan_window_defaults_to_four_days(self) -> None:
        start, end = scan_window(date(2026, 6, 18), horizon_days=3)
        assert start == date(2026, 6, 18)
        assert end == date(2026, 6, 21)

    def test_parse_mcgill_single_day_with_time(self) -> None:
        start, end = parse_mcgill_date_text("Thursday, June 18, 2026 07:30 to 08:30")
        assert start == datetime(2026, 6, 18, 7, 30)
        assert end == datetime(2026, 6, 18, 8, 30)

    def test_parse_mcgill_date_range(self) -> None:
        start, end = parse_mcgill_date_text(
            "Monday, June 15, 2026 to Thursday, June 18, 2026"
        )
        assert start == datetime(2026, 6, 15, 0, 0)
        assert end == datetime(2026, 6, 18, 0, 0)

    def test_parse_concordia_when_single_day(self) -> None:
        start, end = parse_concordia_when("June 18, 2026, 8 a.m. – 10 a.m.")
        assert start == datetime(2026, 6, 18, 8, 0)
        assert end == datetime(2026, 6, 18, 10, 0)


class TestMcGillScraper:
    def test_parse_listing_extracts_core_fields(self, mcgill_html: str) -> None:
        source = McGillEventSource()
        events = source.parse_html(mcgill_html, date(2026, 6, 18), date(2026, 6, 21))

        assert events
        titles = {event.title for event in events}
        assert "PCard Reconciliation in MOPS - Deadline for May Transactions" in titles

        event = next(
            event
            for event in events
            if "PCard Reconciliation" in event.title
        )
        assert event.source == "mcgill"
        assert event.start_at == datetime(2026, 6, 18, 0, 0)
        assert event.url and "mcgill.ca" in event.url
        assert event.description

    def test_filters_outside_window(self, mcgill_html: str) -> None:
        source = McGillEventSource()
        events = source.parse_html(mcgill_html, date(2026, 1, 1), date(2026, 1, 2))
        assert events == []


class TestConcordiaScraper:
    def test_parse_listing_extracts_when_where(self, concordia_html: str) -> None:
        source = ConcordiaEventSource()
        events = source.parse_html(concordia_html, date(2026, 6, 18), date(2026, 6, 21))

        assert events
        event = next(event for event in events if "Register with me" in event.title)
        assert event.location == "Online"
        assert event.start_at == datetime(2026, 6, 18, 8, 0)
        assert event.end_at == datetime(2026, 6, 18, 10, 0)
        assert event.url == "https://www.concordia.ca/cuevents/offices/provost/ssc/2026/06/18/register-with-me.html"

    def test_more_info_url_not_location_link(self, concordia_html: str) -> None:
        source = ConcordiaEventSource()
        events = source.parse_html(concordia_html, date(2026, 6, 18), date(2026, 6, 21))

        event = next(event for event in events if "Un)just Transitions" in event.title)
        assert event.url == (
            "https://www.concordia.ca/cuevents/offices/provost/fourth-space/2026/06/15/unjust-transitions.html"
        )
        assert "/maps/" not in event.url

    def test_includes_ongoing_events_in_window(self, concordia_html: str) -> None:
        source = ConcordiaEventSource()
        events = source.parse_html(concordia_html, date(2026, 6, 18), date(2026, 6, 19))
        titles = " ".join(event.title for event in events)
        assert "Un)just Transitions" in titles
