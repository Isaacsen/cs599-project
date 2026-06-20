from __future__ import annotations

from dataclasses import dataclass

from src.agents.patch_reviewer import PatchReviewReport
from src.agents.sandbox_validator import SandboxValidationReport


@dataclass(frozen=True)
class RepairLoopReport:
    status: str
    iteration: int
    next_step: str
    actions: list[str]


def plan_repair_iteration(
    patch_review: PatchReviewReport | None,
    sandbox_validation: SandboxValidationReport | None,
    max_iterations: int = 1,
) -> RepairLoopReport:
    actions: list[str] = []
    if patch_review is not None and not patch_review.passed:
        actions.append("Review unsafe patch findings before applying fixes.")
    if sandbox_validation is not None and not sandbox_validation.passed:
        actions.extend(sandbox_validation.diagnosis.suggestions)
    if sandbox_validation is None:
        actions.append("Run sandbox validation to verify generated tests under isolation.")

    if not actions:
        return RepairLoopReport(
            status="complete",
            iteration=0,
            next_step="finish",
            actions=["No repair iteration needed; patch review and sandbox validation passed."],
        )
    if max_iterations <= 0:
        return RepairLoopReport(
            status="blocked",
            iteration=0,
            next_step="manual_review",
            actions=actions,
        )
    return RepairLoopReport(
        status="planned",
        iteration=1,
        next_step="fix" if patch_review and not patch_review.passed else "test_plan",
        actions=_dedupe(actions),
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
