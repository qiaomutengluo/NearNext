from __future__ import annotations

import logging
import time
from datetime import datetime

import schedule

from event_workflow.pipeline import EventPipeline, PipelineConfig

logger = logging.getLogger(__name__)


def run_scheduled(
    pipeline: EventPipeline,
    *,
    daily_at: str = "08:00",
    poll_seconds: int = 30,
) -> None:
    """Block and run the pipeline on a daily schedule."""

    def job() -> None:
        logger.info("Scheduled run started at %s", datetime.utcnow().isoformat())
        try:
            pipeline.run()
        except Exception:
            logger.exception("Scheduled pipeline run failed")

    schedule.every().day.at(daily_at).do(job)
    logger.info("Scheduler started; next daily run at %s", daily_at)

    while True:
        schedule.run_pending()
        time.sleep(poll_seconds)
