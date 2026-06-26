from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from event_workflow.dates import DEFAULT_HORIZON_DAYS, scan_window
from event_workflow.filters import (
    filter_by_date_window,
    filter_by_keywords,
    filter_by_sources,
    filter_exclude_cancelled,
    filter_exclude_long_span,
    filter_in_person_only,
    filter_online_only,
)
from event_workflow.interest_filter import DEFAULT_RULES_PATH, FilterRules, FilteredEvent, apply_interest_filter
from event_workflow.llm.analyzer import EventAnalyzer
from event_workflow.models import AnalysisResult, EventRecord
from event_workflow.sources.base import EventSource
from event_workflow.sources.concordia import ConcordiaEventSource
from event_workflow.sources.mcgill import McGillEventSource
from event_workflow.stats import build_event_stats, format_stats_report
from event_workflow.storage import JsonEventStore

logger = logging.getLogger(__name__)


def default_sources() -> list[EventSource]:
    return [McGillEventSource(), ConcordiaEventSource()]


@dataclass
class PipelineConfig:
    data_dir: Path = Path("data")
    horizon_days: int = DEFAULT_HORIZON_DAYS
    sources: list[EventSource] = field(default_factory=default_sources)
    keywords: list[str] = field(default_factory=list)
    online_only: bool = False
    in_person_only: bool = False
    exclude_cancelled: bool = True
    reference_date: date | None = None
    filter_rules_path: Path | None = None


class EventPipeline:
    def __init__(self, config: PipelineConfig, store: JsonEventStore | None = None) -> None:
        self.config = config
        self.store = store or JsonEventStore(config.data_dir)

    def scrape(self) -> list[EventRecord]:
        window_start, window_end = scan_window(
            self.config.reference_date,
            self.config.horizon_days,
        )
        logger.info("Scanning events for %s to %s", window_start, window_end)

        collected: list[EventRecord] = []
        for source in self.config.sources:
            logger.info("Fetching source: %s", source.name)
            events = source.fetch_events(window_start, window_end)
            logger.info("Source %s returned %s events", source.name, len(events))
            collected.extend(events)

        filtered = self.apply_filters(collected, window_start, window_end)
        self.store.save_events(filtered, run_at=datetime.utcnow())
        logger.info("Saved %s events to %s", len(filtered), self.store.events_path)
        return filtered

    def apply_filters(
        self,
        events: list[EventRecord],
        window_start: date,
        window_end: date,
    ) -> list[EventRecord]:
        result = list(events)
        result = filter_by_date_window(result, window_start, window_end)
        if self.config.exclude_cancelled:
            result = filter_exclude_cancelled(result)
        result = filter_exclude_long_span(result)
        if self.config.keywords:
            result = filter_by_keywords(result, self.config.keywords)
        if self.config.online_only:
            result = filter_online_only(result)
        if self.config.in_person_only:
            result = filter_in_person_only(result)
        return result

    def filter_by_interests(
        self,
        events: list[EventRecord] | None = None,
        *,
        rules: FilterRules | None = None,
    ) -> tuple[list[FilteredEvent], dict, str]:
        events = events if events is not None else self.store.load_events()
        if not events:
            raise ValueError("No events available for interest filtering")

        events = filter_exclude_long_span(events)
        rules_path = self.config.filter_rules_path or DEFAULT_RULES_PATH
        rules = rules or FilterRules.load(rules_path)
        window_start, window_end = scan_window(
            self.config.reference_date,
            self.config.horizon_days,
        )

        result = apply_interest_filter(events, rules)
        stats = build_event_stats(events, result.kept, window_start=window_start, window_end=window_end)
        report = format_stats_report(stats)

        self.store.save_filtered_events(
            result.kept,
            rules_path=str(rules_path),
            excluded=result.excluded,
        )
        self.store.save_filter_stats(stats)
        logger.info("Filtered %s -> %s events", len(events), len(result.kept))
        return result.kept, stats, report

    def analyze(self, events: list[EventRecord] | None = None) -> AnalysisResult:
        events = events if events is not None else self.store.load_events()
        if not events:
            raise ValueError("No events available for analysis")

        analyzer = EventAnalyzer.from_env()
        try:
            result = analyzer.analyze(events)
        finally:
            analyzer.client.close()

        self.store.append_analysis(result)
        logger.info("Appended analysis run %s", result.run_id)
        return result

    def run(self) -> tuple[list[EventRecord], AnalysisResult | None]:
        events = self.scrape()
        if not events:
            logger.warning("No events scraped; skipping LLM analysis")
            return events, None
        try:
            analysis = self.analyze(events)
        except ValueError as exc:
            logger.warning("LLM analysis skipped: %s", exc)
            analysis = None
        return events, analysis
