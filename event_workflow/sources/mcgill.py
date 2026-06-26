from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from event_workflow.dates import parse_mcgill_date_text
from event_workflow.models import EventRecord
from event_workflow.sources.base import EventSource

DEFAULT_URL = "https://www.mcgill.ca/channels/section/all/channel_event"
BASE_URL = "https://www.mcgill.ca"
USER_AGENT = "Mozilla/5.0 (compatible; EventWorkflow/1.0; +https://github.com/local)"


class McGillEventSource(EventSource):
    name = "mcgill"

    def __init__(self, url: str = DEFAULT_URL, session: requests.Session | None = None) -> None:
        self.url = url
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    def fetch_events(self, window_start: date, window_end: date) -> list[EventRecord]:
        response = self.session.get(self.url, timeout=30)
        response.raise_for_status()
        return self.parse_html(response.text, window_start, window_end)

    def parse_html(self, html: str, window_start: date, window_end: date) -> list[EventRecord]:
        soup = BeautifulSoup(html, "lxml")
        events: list[EventRecord] = []

        for row in soup.select("div.channel_event.views-row"):
            title_el = row.select_one(".views-field-title a")
            if title_el is None:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = urljoin(BASE_URL, href) if href else None

            date_el = row.select_one(".views-field-field-channels-event-date .field-content")
            raw_date = date_el.get_text(" ", strip=True) if date_el else ""
            start_at, end_at = parse_mcgill_date_text(raw_date)

            body_el = row.select_one(".views-field-body .field-content")
            description = body_el.get_text(" ", strip=True) if body_el else None
            location = _extract_location(description)

            categories = [
                a.get_text(strip=True)
                for a in row.select(".views-field-field-category a")
                if a.get_text(strip=True)
            ]

            record = EventRecord(
                source=self.name,
                title=title,
                start_at=start_at,
                end_at=end_at,
                location=location,
                description=description,
                url=url,
                raw_date_text=raw_date or None,
                categories=categories,
            )
            if record.overlaps_window(window_start, window_end):
                events.append(record)

        return events


def _extract_location(description: str | None) -> str | None:
    if not description:
        return None

    patterns = [
        r"\[Location\s+([^\]]+)\]",
        r"\((online session)\)",
        r"Location:\s*([^\n.]+)",
        r"in (?:the )?([A-Z][A-Za-z0-9' -]+(?:Building|Room|Atrium|Hall)[^.]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    if re.search(r"\bonline\b", description, re.IGNORECASE):
        return "Online"

    return None
