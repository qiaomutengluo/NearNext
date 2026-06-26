from __future__ import annotations

import json

import httpx
import pytest

from event_workflow.llm.agnes_client import AgnesClient, AgnesConfig, parse_json_from_llm
from event_workflow.llm.analyzer import EventAnalyzer
from event_workflow.models import EventRecord
from datetime import datetime


@pytest.fixture
def agnes_config() -> AgnesConfig:
    return AgnesConfig(api_key="test-key", base_url="https://apihub.agnes-ai.com/v1")


def test_chat_completion_request_shape(httpx_mock, agnes_config: AgnesConfig) -> None:
    httpx_mock.add_response(
        url="https://apihub.agnes-ai.com/v1/chat/completions",
        json={
            "choices": [{"message": {"content": '{"summary":"done"}'}}],
        },
    )

    with AgnesClient(agnes_config) as client:
        payload = client.chat_completion(
            [{"role": "user", "content": "hello"}],
            temperature=0.1,
            max_tokens=128,
        )

    assert payload["choices"][0]["message"]["content"] == '{"summary":"done"}'
    request = httpx_mock.get_request()
    body = json.loads(request.content.decode())
    assert body["model"] == "agnes-2.0-flash"
    assert body["messages"][0]["content"] == "hello"


def test_parse_json_from_llm_strips_markdown_fence() -> None:
    text = '```json\n{"summary": "测试"}\n```'
    assert parse_json_from_llm(text)["summary"] == "测试"


def test_event_analyzer_parses_structured_response(httpx_mock, agnes_config: AgnesConfig) -> None:
    analysis = {
        "summary": "今日活动丰富",
        "highlights": [],
        "duplicates": [],
        "recommendations": [],
        "tags": {},
    }
    httpx_mock.add_response(
        url="https://apihub.agnes-ai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": json.dumps(analysis, ensure_ascii=False)}}]},
    )

    events = [
        EventRecord(
            source="mcgill",
            title="Workshop",
            start_at=datetime(2026, 6, 18, 10, 0),
            end_at=None,
            location="Online",
            description="desc",
            url="https://example.com",
        )
    ]

    with AgnesClient(agnes_config) as client:
        analyzer = EventAnalyzer(client)
        result = analyzer.analyze(events)

    assert result.events_analyzed == 1
    assert result.analysis["summary"] == "今日活动丰富"


def test_from_env_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("AGNES_API_KEY", raising=False)
    with pytest.raises(ValueError, match="AGNES_API_KEY"):
        AgnesConfig.from_env()
