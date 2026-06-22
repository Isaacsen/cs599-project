from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_PROVIDER = "dashscope"
DEFAULT_MODELS = {
    "dashscope": "glm-5.2",
    "deepseek": "deepseek-v4-pro",
    "openai": "gpt-4o-mini",
    "ollama": "qwen2.5-coder",
}
DEFAULT_BASE_URLS = {
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434/v1",
}
PROVIDER_ALIASES = {
    "ali": "dashscope",
    "alibaba": "dashscope",
    "aliyun": "dashscope",
    "qwen": "dashscope",
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key_set: bool
    api_key_env: str
    base_url: str = ""
    timeout_seconds: int = 120
    max_retries: int = 1

    @classmethod
    def from_env(cls) -> "LLMConfig":
        provider = normalize_provider(os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER))
        model = os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS.get(provider, "")
        api_key, api_key_env = get_llm_api_key(provider)
        base_url = os.getenv("LLM_BASE_URL", "").strip() or DEFAULT_BASE_URLS.get(provider, "")
        timeout_seconds = _positive_int(os.getenv("LLM_TIMEOUT_SECONDS"), 120)
        max_retries = _positive_int(os.getenv("LLM_MAX_RETRIES"), 1)
        return cls(
            provider=provider,
            model=model,
            api_key_set=bool(api_key),
            api_key_env=api_key_env,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def api_key(self) -> str:
        api_key, _ = get_llm_api_key(self.provider)
        return api_key


def get_llm_api_key(provider: str | None = None) -> tuple[str, str]:
    active_provider = normalize_provider(provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER))
    env_names = _api_key_env_names(active_provider)
    for env_name in env_names:
        value = os.getenv(env_name)
        if value:
            return value, env_name
    return "", env_names[0]


def _api_key_env_names(provider: str) -> list[str]:
    if provider == "dashscope":
        return ["DASHSCOPE_API_KEY", "LLM_API_KEY"]
    if provider == "deepseek":
        return ["DEEPSEEK_API_KEY", "LLM_API_KEY"]
    return [f"{provider.upper()}_API_KEY", "LLM_API_KEY"]


def normalize_provider(provider: str | None) -> str:
    normalized = (provider or DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER
    return PROVIDER_ALIASES.get(normalized, normalized)


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value or "")
    except ValueError:
        return default
    return parsed if parsed > 0 else default
