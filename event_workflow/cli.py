from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from event_workflow.interest_filter import DEFAULT_RULES_PATH
from event_workflow.pipeline import EventPipeline, PipelineConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Campus event scan + LLM analysis workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape", help="Scrape events and export JSON")
    scrape_parser.add_argument("--data-dir", default=os.getenv("EVENT_DATA_DIR", "data"))
    scrape_parser.add_argument("--horizon-days", type=int, default=3)
    scrape_parser.add_argument("--keywords", nargs="*", default=[])
    scrape_parser.add_argument("--online-only", action="store_true")
    scrape_parser.add_argument("--in-person-only", action="store_true")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze exported events with Agnes LLM")
    analyze_parser.add_argument("--data-dir", default=os.getenv("EVENT_DATA_DIR", "data"))
    analyze_parser.add_argument("--filtered", action="store_true", help="Analyze interest-filtered events")

    filter_parser = subparsers.add_parser("filter", help="Apply interest rules and export filtered JSON + stats")
    filter_parser.add_argument("--data-dir", default=os.getenv("EVENT_DATA_DIR", "data"))
    filter_parser.add_argument("--horizon-days", type=int, default=3)
    filter_parser.add_argument(
        "--rules",
        default=os.getenv("EVENT_FILTER_RULES", str(DEFAULT_RULES_PATH)),
        help="Path to filter rules JSON",
    )

    run_parser = subparsers.add_parser("run", help="Scrape then analyze")
    run_parser.add_argument("--data-dir", default=os.getenv("EVENT_DATA_DIR", "data"))
    run_parser.add_argument("--horizon-days", type=int, default=3)
    run_parser.add_argument("--keywords", nargs="*", default=[])
    run_parser.add_argument("--online-only", action="store_true")
    run_parser.add_argument("--in-person-only", action="store_true")

    schedule_parser = subparsers.add_parser("schedule", help="Run workflow daily on a schedule")
    schedule_parser.add_argument("--data-dir", default=os.getenv("EVENT_DATA_DIR", "data"))
    schedule_parser.add_argument("--horizon-days", type=int, default=3)
    schedule_parser.add_argument("--daily-at", default=os.getenv("EVENT_SCHEDULE_TIME", "08:00"))
    schedule_parser.add_argument("--keywords", nargs="*", default=[])
    schedule_parser.add_argument("--online-only", action="store_true")
    schedule_parser.add_argument("--in-person-only", action="store_true")

    return parser


def _config_from_args(args: argparse.Namespace) -> PipelineConfig:
    rules_path = None
    if hasattr(args, "rules") and args.rules:
        rules_path = Path(args.rules)
    return PipelineConfig(
        data_dir=Path(args.data_dir),
        horizon_days=getattr(args, "horizon_days", 3),
        keywords=list(getattr(args, "keywords", []) or []),
        online_only=getattr(args, "online_only", False),
        in_person_only=getattr(args, "in_person_only", False),
        filter_rules_path=rules_path,
    )


def _print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    config = _config_from_args(args)
    pipeline = EventPipeline(config)

    if args.command == "scrape":
        events = pipeline.scrape()
        print(f"Exported {len(events)} events to {config.data_dir}/events.json")
        return 0

    if args.command == "analyze":
        events = None
        if getattr(args, "filtered", False):
            from event_workflow.storage import JsonEventStore

            store = JsonEventStore(config.data_dir)
            if store.filtered_events_path.exists():
                import json

                payload = json.loads(store.filtered_events_path.read_text(encoding="utf-8"))
                from event_workflow.models import EventRecord

                events = [EventRecord.from_dict(item) for item in payload.get("events", [])]
        result = pipeline.analyze(events)
        print(f"Analysis run {result.run_id} saved to {config.data_dir}/analysis.json")
        return 0

    if args.command == "filter":
        _, stats, report = pipeline.filter_by_interests()
        _print(report)
        _print("")
        _print(f"Filtered JSON: {config.data_dir}/events_filtered.json")
        _print(f"Stats JSON:    {config.data_dir}/filter_stats.json")
        return 0

    if args.command == "run":
        events, analysis = pipeline.run()
        print(f"Scraped {len(events)} events")
        try:
            filtered, stats, report = pipeline.filter_by_interests(events)
            _print(report)
            _print(f"Filtered JSON: {config.data_dir}/events_filtered.json")
        except Exception as exc:
            logging.getLogger(__name__).warning("Interest filter skipped: %s", exc)
        if analysis:
            print(f"Analysis run {analysis.run_id} completed")
        return 0

    if args.command == "schedule":
        from event_workflow.scheduler import run_scheduled

        run_scheduled(pipeline, daily_at=args.daily_at)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
