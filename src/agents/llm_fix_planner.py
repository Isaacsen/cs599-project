from __future__ import annotations

from dataclasses import dataclass

from src.agents.code_reviewer import ReviewFinding
from src.agents.llm_code_reviewer import LLMCodeReviewReport
from src.agents.sandbox_validator import SandboxValidationReport


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

    @property
    def target_count(self) -> int:
        return len(self.targets)


def plan_llm_fixes(
    llm_review: LLMCodeReviewReport | None,
    sandbox_validation: SandboxValidationReport | None = None,
    max_targets: int = MAX_FINDINGS_PER_FIX,
) -> LLMFixPlan:
    if llm_review is None or not llm_review.findings:
        return LLMFixPlan(status="no_findings", targets=[], rationale="No LLM review findings are available.")

    ranked = _rank_findings(llm_review.findings, sandbox_validation)
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
    return LLMFixPlan(
        status="planned" if targets else "no_targets",
        targets=targets,
        rationale="Fix higher severity and sandbox-relevant findings first.",
    )


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
