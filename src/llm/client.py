from __future__ import annotations

import json
from typing import Protocol
from urllib import error, request

from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt


class LLMClient(Protocol):
    def generate(self, prompt: LLMTestPrompt) -> str:
        raise NotImplementedError


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig | None = None, timeout_seconds: int = 60) -> None:
        self.config = config or LLMConfig.from_env()
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: LLMTestPrompt) -> str:
        if not self.config.api_key_set and self.config.provider != "ollama":
            raise ValueError(f"Missing API key in {self.config.api_key_env}")
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key():
            headers["Authorization"] = f"Bearer {self.config.api_key()}"

        req = request.Request(
            _chat_completions_url(self.config.base_url),
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        return _extract_chat_content(json.loads(body))


class StaticLLMClient:
    def __init__(self, content: str) -> None:
        self.content = content

    def generate(self, prompt: LLMTestPrompt) -> str:
        return self.content


def _chat_completions_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return f"{cleaned}/chat/completions"


def _extract_chat_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("LLM response did not include choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM response did not include message content.")
    return content
