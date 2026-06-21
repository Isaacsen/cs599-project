from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.code_reviewer import ReviewFinding
from src.llm.client import LLMClient, OpenAICompatibleLLMClient
from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt
from src.tools.repo_scanner import RepositoryScanResult


@dataclass(frozen=True)
class LLMCodeReviewReport:
    project_path: str
    status: str
    provider: str
    model: str
    api_key_set: bool
    api_key_env: str
    findings: list[ReviewFinding]
    raw_response: str = ""

    @property
    def finding_count(self) -> int:
        return len(self.findings)


def review_repository_with_llm(
    project_path: str | Path,
    scan: RepositoryScanResult,
    client: LLMClient | None = None,
    config: LLMConfig | None = None,
    max_files: int = 6,
) -> LLMCodeReviewReport:
    root = Path(project_path).resolve()
    active_config = config or LLMConfig.from_env()
    if client is None and not active_config.api_key_set and active_config.provider != "ollama":
        return LLMCodeReviewReport(
            project_path=str(root),
            status="skipped_missing_api_key",
            provider=active_config.provider,
            model=active_config.model,
            api_key_set=False,
            api_key_env=active_config.api_key_env,
            findings=[],
        )

    prompt = _build_review_prompt(root, scan, max_files=max_files)
    active_client = client or OpenAICompatibleLLMClient(active_config)
    raw_response = active_client.generate(prompt)
    findings = _parse_findings(raw_response)
    return LLMCodeReviewReport(
        project_path=str(root),
        status="reviewed",
        provider=active_config.provider,
        model=active_config.model,
        api_key_set=active_config.api_key_set,
        api_key_env=active_config.api_key_env,
        findings=findings,
        raw_response=raw_response,
    )


def _build_review_prompt(root: Path, scan: RepositoryScanResult, max_files: int) -> LLMTestPrompt:
    chunks: list[str] = []
    for relative_file in scan.source_files[:max_files]:
        path = root / relative_file
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        chunks.append(f"# {relative_file}\n{content[:6000]}")
    user = (
        "Review the following Python source for correctness, security, edge cases, and testability.\n"
        "Return JSON only with this shape:\n"
        '{"findings":[{"file_path":"...","line":1,"severity":"high|medium|low",'
        '"rule":"llm_review","message":"...","suggestion":"..."}]}\n\n'
        + "\n\n".join(chunks)
    )
    return LLMTestPrompt(
        system=(
            "You are Software Engineer Agent Code Review Agent. Produce concise, actionable findings. "
            "Do not include secrets. Return valid JSON only."
        ),
        user=user,
        covered_functions=scan.source_files[:max_files],
    )


def _parse_findings(raw_response: str) -> list[ReviewFinding]:
    payload_text = _extract_json(raw_response)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return [
            ReviewFinding(
                file_path="",
                line=1,
                severity="low",
                rule="llm_review_unstructured",
                message=raw_response.strip()[:240],
                suggestion="Review the unstructured LLM review response manually.",
            )
        ]

    findings: list[ReviewFinding] = []
    for item in payload.get("findings", []):
        if not isinstance(item, dict):
            continue
        findings.append(
            ReviewFinding(
                file_path=str(item.get("file_path", "")),
                line=_positive_int(item.get("line", 1)),
                severity=_severity(item.get("severity", "low")),
                rule=str(item.get("rule", "llm_review")),
                message=str(item.get("message", "")).strip()[:500],
                suggestion=str(item.get("suggestion", "")).strip()[:500],
            )
        )
    return [finding for finding in findings if finding.message]


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


def _positive_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 1
    return max(parsed, 1)


def _severity(value: object) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "low"
