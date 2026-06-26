from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from event_workflow.llm.agnes_client import AgnesClient, AgnesConfig, parse_json_from_llm
from event_workflow.models import AnalysisResult, EventRecord

SYSTEM_PROMPT = """You are a campus events analyst for Montreal universities.
The events you receive have already been rule-filtered for user interests:
AI lectures/workshops, career & job hunting, music, and social events.
Produce structured insights in JSON only.
Return a JSON object with keys:
- summary: short overview in Chinese
- highlights: array of 3-5 notable events with title, reason
- duplicates: array of likely duplicate events across sources
- recommendations: array of personalized suggestions prioritized by user interests
- tags: object mapping event id to suggested tags (array of strings)
Do not include markdown fences."""


class EventAnalyzer:
    def __init__(self, client: AgnesClient) -> None:
        self.client = client

    def analyze(self, events: list[EventRecord]) -> AnalysisResult:
        compact_events = [
            {
                "id": event.id,
                "source": event.source,
                "title": event.title,
                "start_at": event.start_at.isoformat() if event.start_at else None,
                "end_at": event.end_at.isoformat() if event.end_at else None,
                "location": event.location,
                "description": (event.description or "")[:500],
                "url": event.url,
            }
            for event in events
        ]

        user_prompt = (
            "Analyze the following campus events and respond with JSON only:\n"
            f"{json.dumps(compact_events, ensure_ascii=False)}"
        )

        payload = self.client.chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        raw_text = self.client.extract_text(payload)
        analysis = parse_json_from_llm(raw_text)

        return AnalysisResult(
            run_id=str(uuid4()),
            created_at=datetime.utcnow(),
            model=self.client.config.model,
            prompt_summary=f"Analyzed {len(events)} events",
            events_analyzed=len(events),
            analysis=analysis,
            raw_response=raw_text,
        )

    @classmethod
    def from_env(cls) -> EventAnalyzer:
        return cls(AgnesClient(AgnesConfig.from_env()))
