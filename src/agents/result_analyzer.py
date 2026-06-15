from __future__ import annotations

import re
from dataclasses import dataclass

from src.sandbox.local_executor import TestExecutionResult


@dataclass(frozen=True)
class PytestSummary:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    warnings: int = 0
    total: int = 0
    conclusion: str = "unknown"


SUMMARY_PATTERN = re.compile(
    r"=+\s*(?P<body>.+?)\s+in\s+(?P<duration>[0-9.]+)s\s*=+",
    re.IGNORECASE,
)
COUNT_PATTERN = re.compile(
    r"(?P<count>\d+)\s+(?P<kind>passed|failed|errors?|skipped|warnings?)",
    re.IGNORECASE,
)


def analyze_pytest_result(execution: TestExecutionResult) -> PytestSummary:
    output = "\n".join(part for part in (execution.stdout, execution.stderr) if part)
    summary_line = _find_summary_line(output)
    counts = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "warnings": 0,
    }

    if summary_line:
        for match in COUNT_PATTERN.finditer(summary_line):
            kind = match.group("kind").lower()
            normalized = _normalize_kind(kind)
            counts[normalized] += int(match.group("count"))

    if execution.timed_out:
        conclusion = "timeout"
    elif execution.passed:
        conclusion = "passed"
    elif counts["failed"] or counts["errors"]:
        conclusion = "failed"
    else:
        conclusion = "execution_error"

    total = counts["passed"] + counts["failed"] + counts["errors"] + counts["skipped"]
    return PytestSummary(
        passed=counts["passed"],
        failed=counts["failed"],
        errors=counts["errors"],
        skipped=counts["skipped"],
        warnings=counts["warnings"],
        total=total,
        conclusion=conclusion,
    )


def _find_summary_line(output: str) -> str | None:
    matches = list(SUMMARY_PATTERN.finditer(output))
    if not matches:
        return None
    return matches[-1].group("body")


def _normalize_kind(kind: str) -> str:
    if kind.startswith("error"):
        return "errors"
    if kind.startswith("warning"):
        return "warnings"
    return kind
