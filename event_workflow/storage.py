from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from event_workflow.interest_filter import FilteredEvent
from event_workflow.models import AnalysisResult, EventRecord


class JsonEventStore:
    """Append-only JSON storage for events and LLM analysis runs."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.data_dir / "events.json"
        self.filtered_events_path = self.data_dir / "events_filtered.json"
        self.filter_stats_path = self.data_dir / "filter_stats.json"
        self.analysis_path = self.data_dir / "analysis.json"

    def load_events(self) -> list[EventRecord]:
        if not self.events_path.exists():
            return []
        payload = json.loads(self.events_path.read_text(encoding="utf-8"))
        return [EventRecord.from_dict(item) for item in payload.get("events", [])]

    def save_events(self, events: list[EventRecord], *, run_at: datetime | None = None) -> dict:
        run_at = run_at or datetime.utcnow()
        payload = {
            "run_at": run_at.isoformat(),
            "count": len(events),
            "events": [event.to_dict() for event in events],
        }
        self.events_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def save_filtered_events(
        self,
        filtered: list[FilteredEvent],
        *,
        run_at: datetime | None = None,
        rules_path: str | None = None,
        excluded: list[dict] | None = None,
    ) -> dict:
        run_at = run_at or datetime.utcnow()
        payload = {
            "run_at": run_at.isoformat(),
            "rules_path": rules_path,
            "count": len(filtered),
            "events": [item.to_dict() for item in filtered],
            "excluded": excluded or [],
        }
        self.filtered_events_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def save_filter_stats(self, stats: dict) -> dict:
        self.filter_stats_path.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return stats

    def upsert_events(self, new_events: list[EventRecord]) -> list[EventRecord]:
        existing = {self._dedupe_key(event): event for event in self.load_events()}
        for event in new_events:
            existing[self._dedupe_key(event)] = event
        merged = list(existing.values())
        self.save_events(merged)
        return merged

    def load_analysis_runs(self) -> list[AnalysisResult]:
        if not self.analysis_path.exists():
            return []
        payload = json.loads(self.analysis_path.read_text(encoding="utf-8"))
        runs = []
        for item in payload.get("runs", []):
            runs.append(
                AnalysisResult(
                    run_id=item["run_id"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                    model=item["model"],
                    prompt_summary=item["prompt_summary"],
                    events_analyzed=item["events_analyzed"],
                    analysis=item["analysis"],
                    raw_response=item.get("raw_response"),
                )
            )
        return runs

    def append_analysis(self, result: AnalysisResult) -> None:
        runs = self.load_analysis_runs()
        runs.append(result)
        payload = {"runs": [run.to_dict() for run in runs]}
        self.analysis_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _dedupe_key(event: EventRecord) -> str:
        return "|".join(
            [
                event.source,
                event.title.strip().lower(),
                (event.start_at.isoformat() if event.start_at else ""),
                (event.url or ""),
            ]
        )
