from __future__ import annotations

import re
from dataclasses import dataclass

from src.agents.result_analyzer import PytestSummary
from src.sandbox.local_executor import TestExecutionResult


@dataclass(frozen=True)
class FailureDiagnosis:
    status: str
    failure_types: list[str]
    key_findings: list[str]
    suggestions: list[str]


FAILED_LINE_PATTERN = re.compile(r"^FAILED\s+(?P<target>\S+)", re.MULTILINE)
ERROR_LINE_PATTERN = re.compile(r"^ERROR\s+(?P<target>\S+)", re.MULTILINE)
ASSERTION_PATTERN = re.compile(r"AssertionError|assert\s+.+", re.IGNORECASE)
IMPORT_PATTERN = re.compile(r"ImportError|ModuleNotFoundError|No module named", re.IGNORECASE)
ZERO_DIVISION_PATTERN = re.compile(r"ZeroDivisionError|division by zero", re.IGNORECASE)
TIMEOUT_PATTERN = re.compile(r"timed out|timeout", re.IGNORECASE)


def diagnose_failure(
    execution: TestExecutionResult,
    analysis: PytestSummary,
) -> FailureDiagnosis:
    if execution.passed:
        return FailureDiagnosis(
            status="no_issue",
            failure_types=[],
            key_findings=[],
            suggestions=["All tests passed. Keep generated tests as regression coverage."],
        )

    output = "\n".join(part for part in (execution.stdout, execution.stderr) if part)
    failure_types = _classify_failures(output, execution, analysis)
    findings = _extract_findings(output)
    suggestions = _suggest_actions(failure_types, analysis)

    return FailureDiagnosis(
        status="needs_attention",
        failure_types=failure_types,
        key_findings=findings,
        suggestions=suggestions,
    )


def _classify_failures(
    output: str,
    execution: TestExecutionResult,
    analysis: PytestSummary,
) -> list[str]:
    types: list[str] = []
    if execution.timed_out or TIMEOUT_PATTERN.search(output):
        types.append("timeout")
    if IMPORT_PATTERN.search(output):
        types.append("import_error")
    if ASSERTION_PATTERN.search(output):
        types.append("assertion_failure")
    if ZERO_DIVISION_PATTERN.search(output):
        types.append("zero_division")
    if analysis.errors:
        types.append("pytest_error")
    if analysis.failed:
        types.append("pytest_failure")
    if not types:
        types.append("execution_error")
    return _dedupe(types)


def _extract_findings(output: str) -> list[str]:
    findings: list[str] = []
    for pattern in (FAILED_LINE_PATTERN, ERROR_LINE_PATTERN):
        for match in pattern.finditer(output):
            findings.append(match.group("target"))

    if not findings:
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if "Error" in stripped or "FAILED" in stripped or "assert" in stripped:
                findings.append(stripped[:180])
            if len(findings) >= 5:
                break

    return findings[:5]


def _suggest_actions(failure_types: list[str], analysis: PytestSummary) -> list[str]:
    suggestions: list[str] = []
    if "timeout" in failure_types:
        suggestions.append("Inspect loops, blocking I/O, and long-running calls; add timeouts or smaller fixtures.")
    if "import_error" in failure_types:
        suggestions.append("Check module paths and dependencies; ensure tests run from the expected project root.")
    if "assertion_failure" in failure_types:
        suggestions.append("Compare expected behavior with implementation; update code or adjust an invalid generated expectation.")
    if "zero_division" in failure_types:
        suggestions.append("Add input validation or document that zero denominators intentionally raise ZeroDivisionError.")
    if "pytest_error" in failure_types:
        suggestions.append("Fix setup, import, fixture, or collection errors before interpreting assertion failures.")
    if "pytest_failure" in failure_types:
        suggestions.append(f"Review {analysis.failed} failing pytest case(s) and keep passing generated tests as regression checks.")
    if not suggestions:
        suggestions.append("Review stderr/stdout and rerun with JSON reporting enabled for a reproducible trace.")
    return _dedupe(suggestions)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
