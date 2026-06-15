from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt


def write_llm_prompt(
    prompt: LLMTestPrompt,
    output_path: str | Path,
    config: LLMConfig | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "llm_config": asdict(config or LLMConfig.from_env()),
        "prompt": asdict(prompt),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
