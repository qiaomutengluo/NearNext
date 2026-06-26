from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_MODEL = "agnes-2.0-flash"


@dataclass
class AgnesConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> AgnesConfig:
        api_key = os.getenv("AGNES_API_KEY", "")
        if not api_key:
            raise ValueError("AGNES_API_KEY is required for LLM analysis")
        return cls(
            api_key=api_key,
            base_url=os.getenv("AGNES_API_BASE", DEFAULT_BASE_URL).rstrip("/"),
            model=os.getenv("AGNES_MODEL", DEFAULT_MODEL),
            timeout=float(os.getenv("AGNES_TIMEOUT", "60")),
        )


class AgnesClient:
    """OpenAI-compatible client for Agnes 2.0 Flash chat completions."""

    def __init__(self, config: AgnesConfig, client: httpx.Client | None = None) -> None:
        self.config = config
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        return response.json()

    def extract_text(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content", "")).strip()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> AgnesClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def parse_json_from_llm(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
