from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import uuid4


@dataclass
class EventRecord:
    """Normalized event metadata exported to storage."""

    source: str
    title: str
    start_at: datetime | None
    end_at: datetime | None
    location: str | None
    description: str | None
    url: str | None
    raw_date_text: str | None = None
    categories: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("start_at", "end_at", "scraped_at"):
            value = data[key]
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventRecord:
        parsed = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        for key in ("start_at", "end_at", "scraped_at"):
            if parsed.get(key):
                parsed[key] = datetime.fromisoformat(parsed[key])
        return cls(**parsed)

    def overlaps_window(self, window_start: date, window_end: date) -> bool:
        if self.start_at is None and self.end_at is None:
            return True
        event_start = (self.start_at or self.end_at).date()
        event_end = (self.end_at or self.start_at).date()
        return event_start <= window_end and event_end >= window_start


@dataclass
class AnalysisResult:
    """LLM analysis output for a batch of events."""

    run_id: str
    created_at: datetime
    model: str
    prompt_summary: str
    events_analyzed: int
    analysis: dict[str, Any]
    raw_response: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data
