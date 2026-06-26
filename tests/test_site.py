from __future__ import annotations

import json
from pathlib import Path

import pytest

from event_workflow.site import build_site_payload, publish_site

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_data(tmp_path: Path) -> Path:
    filtered_src = Path(__file__).parent.parent / "data" / "events_filtered.json"
    stats_src = Path(__file__).parent.parent / "data" / "filter_stats.json"
    if not filtered_src.exists():
        pytest.skip("sample filtered data not available")

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "events_filtered.json").write_text(
        filtered_src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if stats_src.exists():
        (data_dir / "filter_stats.json").write_text(
            stats_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return data_dir


def test_build_site_payload_excludes_local_paths(sample_data: Path) -> None:
    payload = build_site_payload(
        sample_data / "events_filtered.json",
        sample_data / "filter_stats.json",
    )

    assert payload["count"] > 0
    assert "rules_path" not in payload
    assert "excluded" not in payload
    assert payload["window"]["start"]
    assert payload["events"][0]["title"]


def test_publish_site_writes_docs(sample_data: Path, tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    events_path = publish_site(data_dir=sample_data, docs_dir=docs_dir)

    assert events_path.exists()
    assert (docs_dir / "index.html").exists()
    assert (docs_dir / "style.css").exists()
    assert (docs_dir / "app.js").exists()

    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert payload["events"]
