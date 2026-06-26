from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from event_workflow.models import EventRecord


class EventSource(ABC):
    """Pluggable event data source."""

    name: str

    @abstractmethod
    def fetch_events(self, window_start: date, window_end: date) -> list[EventRecord]:
        """Return events that overlap [window_start, window_end]."""
