from __future__ import annotations

from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from event_workflow.dates import parse_concordia_when
from event_workflow.models import EventRecord
from event_workflow.sources.base import EventSource

DEFAULT_URL = "https://www.concordia.ca/events.html"
BASE_URL = "https://www.concordia.ca"
USER_AGENT = "Mozilla/5.0 (compatible; EventWorkflow/1.0; +https://github.com/local)"


class ConcordiaEventSource(EventSource):
    name = "concordia"

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

        for item in soup.select(".list-events .accordion-item"):
            title_el = item.select_one(".accordion-header .title span")
            if title_el is None:
                continue

            title = title_el.get_text(strip=True)
            time_label_el = item.select_one(".accordion-header .label")
            time_label = time_label_el.get_text(" ", strip=True) if time_label_el else None

            when_text = _group_value(item, "When")
            where_text = _group_value(item, "Where")
            description = _first_paragraph(item)
            url = _more_info_url(item)

            start_at, end_at = parse_concordia_when(when_text or "")
            raw_date = when_text
            if time_label and raw_date:
                raw_date = f"{time_label} | {raw_date}"

            categories: list[str] = []
            metadata = item.select_one(".filterMetadata")
            if metadata:
                for span in metadata.select("span"):
                    label = span.get("class", [""])[0]
                    value = span.get_text(" ", strip=True)
                    if value:
                        categories.append(f"{label}:{value}")

            record = EventRecord(
                source=self.name,
                title=title,
                start_at=start_at,
                end_at=end_at,
                location=where_text,
                description=description,
                url=url,
                raw_date_text=raw_date,
                categories=categories,
            )
            if record.overlaps_window(window_start, window_end):
                events.append(record)

        return events


def _more_info_url(item: BeautifulSoup) -> str | None:
    for link in item.select(".accordion-body a[href]"):
        if link.get_text(strip=True).lower() == "more info":
            return urljoin(BASE_URL, link["href"])
    return None


def _group_value(item: BeautifulSoup, label: str) -> str | None:
    for group in item.select(".accordion-body .group"):
        label_el = group.select_one(".label")
        if label_el and label_el.get_text(strip=True).lower() == label.lower():
            value_el = group.select_one(".rte")
            if value_el:
                return value_el.get_text(" ", strip=True)
    return None


def _first_paragraph(item: BeautifulSoup) -> str | None:
    for group in item.select(".accordion-body .group"):
        label_el = group.select_one(".label")
        if label_el and label_el.get_text(strip=True):
            continue
        paragraph = group.select_one(".rte p")
        if paragraph:
            text = paragraph.get_text(" ", strip=True)
            if text:
                return text
    return None
