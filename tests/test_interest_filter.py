from __future__ import annotations

from datetime import date, datetime

from event_workflow.interest_filter import FilterRules, apply_interest_filter
from event_workflow.models import EventRecord
from event_workflow.stats import build_event_stats, format_stats_report


def _event(title: str, description: str | None = None, source: str = "mcgill") -> EventRecord:
    return EventRecord(
        source=source,
        title=title,
        start_at=datetime(2026, 6, 18, 10, 0),
        end_at=datetime(2026, 6, 18, 12, 0),
        location="Online",
        description=description,
        url="https://example.com",
    )


def test_exclude_phd_and_campus_tour() -> None:
    rules = FilterRules(
        exclude_keywords=["phd oral", "campus tour", "scholarship"],
        exclude_title_keywords=["oral exam"],
        interests={"ai": {"label": "AI", "keywords": [" ai "]}, "social": {"label": "社交", "keywords": ["social"]}},
    )
    events = [
        _event("PhD Oral Exam - Someone"),
        _event("Campus tour: Loyola"),
        _event("AI workshop on generative models", "Introduction to AI tools"),
        _event("Black Alumni Summer social"),
    ]
    result = apply_interest_filter(events, rules)
    assert len(result.kept) == 2
    assert result.kept[0].interests == ["ai"]
    assert result.kept[1].interests == ["social"]
    assert len(result.excluded) == 2


def test_no_interest_match_excluded() -> None:
    rules = FilterRules(
        exclude_keywords=[],
        exclude_title_keywords=[],
        interests={"music": {"label": "音乐", "keywords": ["concert"]}},
    )
    result = apply_interest_filter([_event("Random admin meeting")], rules)
    assert result.kept == []
    assert result.excluded[0]["reason"] == "no_interest_match"


def test_stats_daily_breakdown() -> None:
    from event_workflow.interest_filter import FilteredEvent

    events = [
        EventRecord(
            source="mcgill",
            title="A",
            start_at=datetime(2026, 6, 18, 10, 0),
            end_at=datetime(2026, 6, 18, 12, 0),
            location=None,
            description=None,
            url=None,
        ),
        EventRecord(
            source="concordia",
            title="B",
            start_at=datetime(2026, 6, 20, 10, 0),
            end_at=None,
            location=None,
            description=None,
            url=None,
        ),
    ]
    filtered = [FilteredEvent(event=events[0], interests=["social"], interest_labels=["社交"])]
    stats = build_event_stats(
        events,
        filtered,
        window_start=date(2026, 6, 18),
        window_end=date(2026, 6, 21),
    )
    assert stats["totals"]["all_events"] == 2
    assert stats["totals"]["filtered_events"] == 1
    assert stats["daily"]["all"]["2026-06-18"] == 1
    assert stats["daily"]["filtered"]["2026-06-18"] == 1
    report = format_stats_report(stats)
    assert "2026-06-18" in report
