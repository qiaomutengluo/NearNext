from __future__ import annotations

from datetime import datetime

from event_workflow.models import EventRecord
from event_workflow.storage import JsonEventStore


def _sample_event(title: str = "Sample Event", source: str = "mcgill") -> EventRecord:
    return EventRecord(
        source=source,
        title=title,
        start_at=datetime(2026, 6, 18, 10, 0),
        end_at=datetime(2026, 6, 18, 12, 0),
        location="Online",
        description="A test event",
        url="https://example.com/event",
    )


def test_save_and_load_events(tmp_path) -> None:
    store = JsonEventStore(tmp_path)
    events = [_sample_event(), _sample_event(title="Another", source="concordia")]
    store.save_events(events)

    loaded = store.load_events()
    assert len(loaded) == 2
    assert loaded[0].title in {"Sample Event", "Another"}


def test_upsert_deduplicates_by_source_title_date_url(tmp_path) -> None:
    store = JsonEventStore(tmp_path)
    first = _sample_event()
    second = _sample_event()
    second.description = "Updated description"

    store.upsert_events([first])
    merged = store.upsert_events([second])

    assert len(merged) == 1
    assert merged[0].description == "Updated description"


def test_append_analysis_run(tmp_path) -> None:
    from event_workflow.models import AnalysisResult

    store = JsonEventStore(tmp_path)
    result = AnalysisResult(
        run_id="run-1",
        created_at=datetime(2026, 6, 18, 12, 0),
        model="agnes-2.0-flash",
        prompt_summary="test",
        events_analyzed=1,
        analysis={"summary": "ok"},
        raw_response='{"summary":"ok"}',
    )
    store.append_analysis(result)

    runs = store.load_analysis_runs()
    assert len(runs) == 1
    assert runs[0].analysis["summary"] == "ok"
