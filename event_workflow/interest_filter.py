from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from event_workflow.models import EventRecord

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "filter_rules.json"


@dataclass
class FilterRules:
    exclude_keywords: list[str] = field(default_factory=list)
    exclude_title_keywords: list[str] = field(default_factory=list)
    interests: dict[str, dict[str, str | list[str]]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> FilterRules:
        exclude = data.get("exclude", {})
        return cls(
            exclude_keywords=[k.lower() for k in exclude.get("keywords", [])],
            exclude_title_keywords=[k.lower() for k in exclude.get("title_keywords", [])],
            interests=data.get("interests", {}),
        )

    @classmethod
    def load(cls, path: str | Path | None = None) -> FilterRules:
        rules_path = Path(path) if path else DEFAULT_RULES_PATH
        payload = json.loads(rules_path.read_text(encoding="utf-8"))
        return cls.from_dict(payload)


@dataclass
class FilteredEvent:
    event: EventRecord
    interests: list[str]
    interest_labels: list[str]

    def to_dict(self) -> dict:
        data = self.event.to_dict()
        data["matched_interests"] = self.interests
        data["interest_labels"] = self.interest_labels
        return data


@dataclass
class InterestFilterResult:
    kept: list[FilteredEvent]
    excluded: list[dict]

    @property
    def events(self) -> list[EventRecord]:
        return [item.event for item in self.kept]


def _haystack(event: EventRecord) -> str:
    return " ".join(
        filter(
            None,
            [
                event.title,
                event.description,
                event.location,
                " ".join(event.categories),
            ],
        )
    ).lower()


def _title_haystack(event: EventRecord) -> str:
    return event.title.lower()


def _match_any(text: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None


def _match_interests(
    text: str,
    interests: dict[str, dict[str, str | list[str]]],
) -> list[tuple[str, str]]:
    matched: list[tuple[str, str]] = []
    for key, config in interests.items():
        keywords = [k.lower() for k in config.get("keywords", [])]  # type: ignore[union-attr]
        if _match_any(text, keywords):
            label = str(config.get("label", key))
            matched.append((key, label))
    return matched


def apply_interest_filter(
    events: list[EventRecord],
    rules: FilterRules | None = None,
) -> InterestFilterResult:
    rules = rules or FilterRules.load()
    kept: list[FilteredEvent] = []
    excluded: list[dict] = []

    for event in events:
        text = _haystack(event)
        title = _title_haystack(event)

        exclude_reason = _match_any(text, rules.exclude_keywords)
        if exclude_reason is None:
            exclude_reason = _match_any(title, rules.exclude_title_keywords)

        if exclude_reason:
            excluded.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "source": event.source,
                    "reason": "exclude",
                    "matched_rule": exclude_reason,
                }
            )
            continue

        interest_matches = _match_interests(text, rules.interests)
        if not interest_matches:
            excluded.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "source": event.source,
                    "reason": "no_interest_match",
                    "matched_rule": None,
                }
            )
            continue

        kept.append(
            FilteredEvent(
                event=event,
                interests=[key for key, _ in interest_matches],
                interest_labels=[label for _, label in interest_matches],
            )
        )

    return InterestFilterResult(kept=kept, excluded=excluded)
