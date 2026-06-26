from __future__ import annotations

import json
import shutil
from pathlib import Path

DEFAULT_DOCS_DIR = Path("docs")
ASSETS = ("index.html", "style.css", "app.js")


def build_site_payload(
    filtered_path: Path,
    stats_path: Path | None = None,
) -> dict:
    filtered = json.loads(filtered_path.read_text(encoding="utf-8"))
    stats = {}
    if stats_path and stats_path.exists():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))

    return {
        "run_at": filtered.get("run_at"),
        "count": filtered.get("count", 0),
        "window": stats.get("window", {}),
        "totals": stats.get("totals", {}),
        "by_source": stats.get("by_source", {}).get("filtered", {}),
        "by_interest": stats.get("by_interest", {}),
        "events": filtered.get("events", []),
    }


def publish_site(
    *,
    data_dir: Path,
    docs_dir: Path = DEFAULT_DOCS_DIR,
    template_dir: Path | None = None,
) -> Path:
    """Copy static assets and write events.json for GitHub Pages."""
    filtered_path = data_dir / "events_filtered.json"
    if not filtered_path.exists():
        raise FileNotFoundError(
            f"Missing {filtered_path}. Run `python -m event_workflow.cli filter` first."
        )

    stats_path = data_dir / "filter_stats.json"
    payload = build_site_payload(filtered_path, stats_path)

    docs_dir.mkdir(parents=True, exist_ok=True)
    source_dir = template_dir or Path(__file__).resolve().parent / "site_assets"
    for name in ASSETS:
        shutil.copy2(source_dir / name, docs_dir / name)

    events_path = docs_dir / "events.json"
    events_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return events_path
