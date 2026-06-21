from __future__ import annotations

from dataclasses import dataclass

from src.agents.sandbox_validator import SandboxValidationReport


@dataclass(frozen=True)
class RepairLoopReport:
    status: str
    iteration: int
    next_step: str
    actions: list[str]


def plan_repair_iteration(
    sandbox_validation: SandboxValidationReport | None,
    current_iteration: int = 0,
    max_iterations: int = 1,
) -> RepairLoopReport:
    actions: list[str] = []
    if sandbox_validation is not None and not sandbox_validation.passed:
        actions.extend(sandbox_validation.diagnosis.suggestions)
    if sandbox_validation is None:
        actions.append("Run sandbox validation to verify generated tests under isolation.")

    if not actions:
        return RepairLoopReport(
            status="complete",
            iteration=current_iteration,
            next_step="finish",
            actions=["No repair iteration needed; sandbox validation passed."],
        )
    if sandbox_validation is None:
        return RepairLoopReport(
            status="planned",
            iteration=current_iteration,
            next_step="sandbox_validate",
            actions=_dedupe(actions),
        )
    if current_iteration >= max_iterations:
        return RepairLoopReport(
            status="blocked",
            iteration=current_iteration,
            next_step="manual_review",
            actions=actions,
        )
    return RepairLoopReport(
        status="planned",
        iteration=current_iteration + 1,
        next_step="llm_tests",
        actions=_dedupe(
            [
                *actions,
                "Regenerate LLM tests with the sandbox failure context, then validate again.",
            ]
        ),
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
