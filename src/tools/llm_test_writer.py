from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.llm_test_generator import LLMTestGenerationReport


def llm_test_report_to_dict(report: LLMTestGenerationReport) -> dict[str, Any]:
    return {
        "project_path": report.project_path,
        "status": report.status,
        "applied": report.applied,
        "test_file_path": report.test_file_path,
        "summary": {
            "generated_test_count": report.generated_test_count,
            "security_check_passed": report.security_check.passed if report.security_check else None,
            "error_summary": report.error_summary,
        },
        "llm_config": {
            "provider": report.provider,
            "model": report.model,
            "api_key_set": report.api_key_set,
            "api_key_env": report.api_key_env,
        },
        "test_plan": asdict(report.test_plan),
        "prompt": _prompt_summary(report.prompt),
        "security_check": asdict(report.security_check) if report.security_check else None,
        "suite": _suite_summary(report.suite),
    }


def _prompt_summary(prompt: Any) -> dict[str, Any]:
    return {
        "covered_functions": list(prompt.covered_functions),
        "system_char_count": len(prompt.system),
        "user_char_count": len(prompt.user),
    }


def _suite_summary(suite: Any) -> dict[str, Any] | None:
    if suite is None:
        return None
    return {
        "test_file_name": suite.test_file_name,
        "test_count": suite.test_count,
        "covered_functions": list(suite.covered_functions),
        "content_sha256": hashlib.sha256(suite.content.encode("utf-8")).hexdigest(),
        "content_char_count": len(suite.content),
    }


def write_llm_test_report(report: LLMTestGenerationReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(llm_test_report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
