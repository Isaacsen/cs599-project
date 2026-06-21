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
    next_step = _next_step_for_failure(sandbox_validation)
    if next_step == "manual_review":
        return RepairLoopReport(
            status="blocked",
            iteration=current_iteration,
            next_step="manual_review",
            actions=_dedupe(
                [
                    *actions,
                    "The failure looks environment-specific or ambiguous; inspect it before another LLM retry.",
                ]
            ),
        )
    return RepairLoopReport(
        status="planned",
        iteration=current_iteration + 1,
        next_step=next_step,
        actions=_dedupe([*actions, _next_step_action(next_step)]),
    )


def _next_step_for_failure(sandbox_validation: SandboxValidationReport | None) -> str:
    if sandbox_validation is None:
        return "sandbox_validate"
    if any(check is not None and not check.passed for check in sandbox_validation.security_checks):
        return "llm_tests"

    failure_types = set(sandbox_validation.diagnosis.failure_types)
    test_generation_failures = {"import_error", "pytest_error"}
    code_fix_failures = {"assertion_failure", "zero_division", "timeout", "pytest_failure"}

    if failure_types & test_generation_failures:
        return "llm_tests"
    if failure_types & code_fix_failures:
        return "llm_fix"
    return "manual_review"


def _next_step_action(next_step: str) -> str:
    if next_step == "llm_tests":
        return "Regenerate LLM tests with the sandbox failure context, then validate again."
    if next_step == "llm_fix":
        return "Send sandbox failure context to the LLM fix agent, then regenerate tests and validate again."
    if next_step == "sandbox_validate":
        return "Run sandbox validation before planning another repair step."
    return "Inspect the failure manually before another LLM retry."


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
