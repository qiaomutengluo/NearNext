from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from event_workflow.models import EventRecord
from event_workflow.pipeline import EventPipeline, PipelineConfig
from datetime import datetime


@freeze_time("2026-06-18 09:00:00")
def test_pipeline_scrape_uses_window_and_saves(tmp_path: Path, mcgill_html: str, concordia_html: str) -> None:
    mcgill = MagicMock()
    mcgill.name = "mcgill"
    mcgill.fetch_events.return_value = [
        EventRecord(
            source="mcgill",
            title="Test",
            start_at=datetime(2026, 6, 18, 10, 0),
            end_at=None,
            location="Online",
            description="d",
            url="https://mcgill.ca/x",
        )
    ]

    concordia = MagicMock()
    concordia.name = "concordia"
    concordia.fetch_events.return_value = []

    config = PipelineConfig(data_dir=tmp_path, sources=[mcgill, concordia])
    pipeline = EventPipeline(config)
    events = pipeline.scrape()

    assert len(events) == 1
    mcgill.fetch_events.assert_called_once_with(date(2026, 6, 18), date(2026, 6, 24))
    assert (tmp_path / "events.json").exists()


@pytest.fixture
def mcgill_html() -> str:
    return (Path(__file__).parent / "fixtures" / "mcgill_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def concordia_html() -> str:
    return (Path(__file__).parent / "fixtures" / "concordia_sample.html").read_text(encoding="utf-8")
