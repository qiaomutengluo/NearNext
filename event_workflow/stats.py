from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from event_workflow.interest_filter import FilteredEvent
from event_workflow.models import EventRecord


def _event_days(event: EventRecord, window_start: date, window_end: date) -> list[date]:
    if event.start_at is None and event.end_at is None:
        return [window_start]

    start = (event.start_at or event.end_at).date()
    end = (event.end_at or event.start_at).date()
    start = max(start, window_start)
    end = min(end, window_end)

    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def build_event_stats(
    all_events: list[EventRecord],
    filtered: list[FilteredEvent],
    *,
    window_start: date,
    window_end: date,
) -> dict[str, Any]:
    filtered_ids = {item.event.id for item in filtered}
    filtered_events = [item.event for item in filtered]

    daily_all: dict[str, int] = defaultdict(int)
    daily_filtered: dict[str, int] = defaultdict(int)
    daily_by_source_all: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    daily_by_source_filtered: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    current = window_start
    while current <= window_end:
        key = current.isoformat()
        daily_all[key] = 0
        daily_filtered[key] = 0
        current += timedelta(days=1)

    for event in all_events:
        for day in _event_days(event, window_start, window_end):
            key = day.isoformat()
            daily_all[key] += 1
            daily_by_source_all[key][event.source] += 1

    for event in filtered_events:
        for day in _event_days(event, window_start, window_end):
            key = day.isoformat()
            daily_filtered[key] += 1
            daily_by_source_filtered[key][event.source] += 1

    by_interest: dict[str, int] = defaultdict(int)
    for item in filtered:
        for interest in item.interests:
            by_interest[interest] += 1

    return {
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "totals": {
            "all_events": len(all_events),
            "filtered_events": len(filtered),
            "excluded_events": len(all_events) - len(filtered),
            "retention_rate": round(len(filtered) / len(all_events), 4) if all_events else 0,
        },
        "by_source": {
            "all": _count_by_source(all_events),
            "filtered": _count_by_source(filtered_events),
        },
        "by_interest": dict(by_interest),
        "daily": {
            "all": dict(daily_all),
            "filtered": dict(daily_filtered),
            "all_by_source": {k: dict(v) for k, v in daily_by_source_all.items()},
            "filtered_by_source": {k: dict(v) for k, v in daily_by_source_filtered.items()},
        },
    }


def _count_by_source(events: list[EventRecord]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        counts[event.source] += 1
    return dict(counts)


def format_stats_report(stats: dict[str, Any]) -> str:
    lines = [
        f"窗口: {stats['window']['start']} ~ {stats['window']['end']}",
        "",
        "总计:",
        f"  全部活动: {stats['totals']['all_events']}",
        f"  筛选后:   {stats['totals']['filtered_events']}",
        f"  排除:     {stats['totals']['excluded_events']}",
        f"  保留率:   {stats['totals']['retention_rate']:.1%}",
        "",
        "按来源:",
        f"  全部     McGill={stats['by_source']['all'].get('mcgill', 0)}, "
        f"Concordia={stats['by_source']['all'].get('concordia', 0)}",
        f"  筛选后   McGill={stats['by_source']['filtered'].get('mcgill', 0)}, "
        f"Concordia={stats['by_source']['filtered'].get('concordia', 0)}",
    ]

    if stats.get("by_interest"):
        lines.extend(["", "兴趣分布 (筛选后):"])
        for key, count in sorted(stats["by_interest"].items(), key=lambda x: -x[1]):
            lines.append(f"  {key}: {count}")

    lines.extend(["", "每日明细 (全部 / 筛选后):"])
    for day in sorted(stats["daily"]["all"].keys()):
        all_count = stats["daily"]["all"][day]
        filtered_count = stats["daily"]["filtered"].get(day, 0)
        lines.append(f"  {day}: {all_count} / {filtered_count}")

    return "\n".join(lines)
