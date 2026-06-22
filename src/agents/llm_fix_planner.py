from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.agents.code_reviewer import ReviewFinding
from src.agents.llm_code_reviewer import LLMCodeReviewReport
from src.agents.sandbox_validator import SandboxValidationReport
from src.llm.client import LLMClient, OpenAICompatibleLLMClient
from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt


MAX_FINDINGS_PER_FIX = 2
SEVERITY_PRIORITY = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class LLMFixTarget:
    finding_index: int
    file_path: str
    line: int
    severity: str
    rule: str
    reason: str


@dataclass(frozen=True)
class LLMFixPlan:
    status: str
    targets: list[LLMFixTarget]
    rationale: str
    remaining_count: int = 0
    planner: str = "rule"
    raw_response: str = ""
    fallback_reason: str = ""

    @property
    def target_count(self) -> int:
        return len(self.targets)


def plan_llm_fixes(
    llm_review: LLMCodeReviewReport | None,
    sandbox_validation: SandboxValidationReport | None = None,
    max_targets: int = MAX_FINDINGS_PER_FIX,
    exclude_finding_indexes: set[int] | None = None,
    client: LLMClient | None = None,
    config: LLMConfig | None = None,
) -> LLMFixPlan:
    if llm_review is None or not llm_review.findings:
        return LLMFixPlan(
            status="no_findings",
            targets=[],
            rationale="No LLM review findings are available.",
        )

    excluded = exclude_finding_indexes or set()
    ranked = [
        item
        for item in _rank_findings(llm_review.findings, sandbox_validation)
        if item[0] not in excluded
    ]
    if not ranked:
        return LLMFixPlan(
            status="no_targets",
            targets=[],
            rationale="All review findings have already been attempted.",
            remaining_count=0,
            planner="rule",
        )
    active_config = config or LLMConfig.from_env()
    fallback_reason = "LLM planner skipped because no API key is configured."
    if client is not None or active_config.api_key_set or active_config.provider == "ollama":
        llm_plan, fallback_reason = _plan_with_llm(
            llm_review,
            ranked,
            sandbox_validation,
            max_targets,
            client=client,
            config=active_config,
        )
        if llm_plan is not None:
            return llm_plan

    return _plan_with_rules(ranked, sandbox_validation, max_targets, fallback_reason=fallback_reason)


def _plan_with_rules(
    ranked: list[tuple[int, ReviewFinding]],
    sandbox_validation: SandboxValidationReport | None,
    max_targets: int,
    fallback_reason: str = "",
) -> LLMFixPlan:
    targets = [
        LLMFixTarget(
            finding_index=index,
            file_path=finding.file_path,
            line=finding.line,
            severity=finding.severity,
            rule=finding.rule,
            reason=_target_reason(finding, sandbox_validation),
        )
        for index, finding in ranked[:max_targets]
    ]
    remaining_count = max(0, len(ranked) - len(targets))
    return LLMFixPlan(
        status="planned" if targets else "no_targets",
        targets=targets,
        rationale="Fix higher severity and sandbox-relevant findings first.",
        remaining_count=remaining_count,
        planner="rule",
        fallback_reason=fallback_reason,
    )


def _plan_with_llm(
    llm_review: LLMCodeReviewReport,
    candidates: list[tuple[int, ReviewFinding]],
    sandbox_validation: SandboxValidationReport | None,
    max_targets: int,
    client: LLMClient | None,
    config: LLMConfig,
) -> tuple[LLMFixPlan | None, str]:
    prompt = _build_planner_prompt(llm_review, candidates, sandbox_validation, max_targets)
    active_client = client or OpenAICompatibleLLMClient(
        config,
        timeout_seconds=min(config.timeout_seconds, 45),
        max_retries=min(config.max_retries, 1),
    )
    try:
        raw_response = active_client.generate(prompt)
    except Exception as exc:
        return None, f"LLM planner failed: {exc}"
    indexes, rationale = _parse_planner_response(raw_response, {index for index, _finding in candidates}, max_targets)
    if not indexes:
        return None, "LLM planner returned no valid target indexes."
    finding_by_index = dict(candidates)
    targets = [
        LLMFixTarget(
            finding_index=index,
            file_path=finding_by_index[index].file_path,
            line=finding_by_index[index].line,
            severity=finding_by_index[index].severity,
            rule=finding_by_index[index].rule,
            reason=rationale or "Selected by LLM fix planner.",
        )
        for index in indexes
    ]
    return LLMFixPlan(
        status="planned",
        targets=targets,
        rationale=rationale or "Selected by LLM fix planner.",
        remaining_count=max(0, len(candidates) - len(targets)),
        planner="llm",
        raw_response=raw_response,
    ), ""


def selected_findings(
    llm_review: LLMCodeReviewReport | None,
    plan: LLMFixPlan | None,
) -> list[ReviewFinding]:
    if llm_review is None or plan is None:
        return []
    findings: list[ReviewFinding] = []
    for target in plan.targets:
        if 0 <= target.finding_index < len(llm_review.findings):
            findings.append(llm_review.findings[target.finding_index])
    return findings


def _rank_findings(
    findings: list[ReviewFinding],
    sandbox_validation: SandboxValidationReport | None,
) -> list[tuple[int, ReviewFinding]]:
    sandbox_text = _sandbox_text(sandbox_validation)
    indexed = list(enumerate(findings))
    return sorted(
        indexed,
        key=lambda item: (
            _sandbox_relevance(item[1], sandbox_text),
            SEVERITY_PRIORITY.get(item[1].severity, 3),
            item[1].file_path,
            item[1].line,
        ),
    )


def _sandbox_relevance(finding: ReviewFinding, sandbox_text: str) -> int:
    if not sandbox_text:
        return 1
    haystack = sandbox_text.lower()
    if finding.file_path and finding.file_path.lower() in haystack:
        return 0
    if finding.rule and finding.rule.lower() in haystack:
        return 0
    return 1


def _sandbox_text(sandbox_validation: SandboxValidationReport | None) -> str:
    if sandbox_validation is None:
        return ""
    parts = [
        " ".join(sandbox_validation.diagnosis.failure_types),
        " ".join(sandbox_validation.diagnosis.key_findings),
        sandbox_validation.execution.stdout,
        sandbox_validation.execution.stderr,
    ]
    return "\n".join(part for part in parts if part)


def _target_reason(finding: ReviewFinding, sandbox_validation: SandboxValidationReport | None) -> str:
    if sandbox_validation is not None and not sandbox_validation.passed:
        return "Selected because the latest sandbox failure may be related to this review finding."
    return f"Selected because it is a {finding.severity} severity review finding."


def _build_planner_prompt(
    llm_review: LLMCodeReviewReport,
    candidates: list[tuple[int, ReviewFinding]],
    sandbox_validation: SandboxValidationReport | None,
    max_targets: int,
) -> LLMTestPrompt:
    findings = [
        {
            "index": index,
            "file_path": finding.file_path,
            "line": finding.line,
            "severity": finding.severity,
            "message": finding.message,
            "suggestion": finding.suggestion,
        }
        for index, finding in candidates[:12]
    ]
    sandbox = {
        "status": sandbox_validation.status,
        "failure_types": sandbox_validation.diagnosis.failure_types,
        "key_findings": sandbox_validation.diagnosis.key_findings[:5],
    } if sandbox_validation is not None else {"status": "not_run"}
    user = (
        "Choose the next findings for the Code Fix Agent. "
        f"Select at most {max_targets} finding indexes. Prefer fixes that unlock failing sandbox tests, "
        "then high severity, then low-risk isolated changes. Return JSON only with this shape:\n"
        '{"target_indexes":[0],"rationale":"why these should be fixed now"}\n\n'
        f"Review status: {llm_review.status}\n"
        f"Sandbox summary: {json.dumps(sandbox, ensure_ascii=False)}\n"
        f"Candidate findings: {json.dumps(findings, ensure_ascii=False)}"
    )
    return LLMTestPrompt(
        system=(
            "You are Software Engineer Agent Fix Planner. Choose a small, ordered batch of review findings "
            "for the next code-fix attempt. Return valid JSON only."
        ),
        user=user,
        covered_functions=[finding.file_path for _index, finding in candidates[:max_targets]],
    )


def _parse_planner_response(raw_response: str, allowed_indexes: set[int], max_targets: int) -> tuple[list[int], str]:
    payload_text = _extract_json(raw_response)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return [], ""
    indexes: list[int] = []
    for value in payload.get("target_indexes", []):
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if index in allowed_indexes and index not in indexes:
            indexes.append(index)
        if len(indexes) >= max_targets:
            break
    rationale = str(payload.get("rationale", "")).strip()[:500]
    return indexes, rationale


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()
