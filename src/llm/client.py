from __future__ import annotations

import json
import os
import time
from typing import Protocol
from urllib import error, request

from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt
from src.llm.streaming import emit_llm_token, has_llm_token_sink


class LLMClient(Protocol):
    def generate(self, prompt: LLMTestPrompt) -> str:
        raise NotImplementedError


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        config: LLMConfig | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.config = config or LLMConfig.from_env()
        self.timeout_seconds = timeout_seconds or self.config.timeout_seconds
        self.max_retries = max_retries if max_retries is not None else self.config.max_retries

    def generate(self, prompt: LLMTestPrompt) -> str:
        if not self.config.api_key_set and self.config.provider != "ollama":
            raise ValueError(f"Missing API key in {self.config.api_key_env}")
        stream_stdout = os.getenv("LLM_STREAM_STDOUT", "").strip() == "1"
        stream_tokens = stream_stdout or has_llm_token_sink()
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "temperature": 0.2,
            "stream": stream_tokens,
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
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    if stream_tokens:
                        return _read_streaming_content(response, emit_stdout=stream_stdout)
                    body = response.read().decode("utf-8")
                return _extract_chat_content(json.loads(body))
            except (error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 4))
                    continue
                raise RuntimeError(f"LLM request failed after {attempt + 1} attempt(s): {exc}") from exc

        raise RuntimeError(f"LLM request failed: {last_error}")


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


def _read_streaming_content(response: object, emit_stdout: bool = False) -> str:
    chunks: list[str] = []
    if emit_stdout:
        print("[llm-stream] ", end="", flush=True)
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        delta = (payload.get("choices") or [{}])[0].get("delta") or {}
        content = delta.get("content") or ""
        if content:
            chunks.append(content)
            emit_llm_token(content)
            if emit_stdout:
                print(content, end="", flush=True)
    if emit_stdout:
        print("", flush=True)
    result = "".join(chunks)
    if not result.strip():
        raise ValueError("LLM streaming response did not include message content.")
    return result
