from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key_set: bool

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("LLM_PROVIDER", "deepseek"),
            model=os.getenv("LLM_MODEL", ""),
            api_key_set=bool(os.getenv("LLM_API_KEY")),
        )
