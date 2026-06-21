from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.security_checker import SecurityCheckResult, check_generated_test_code
from src.agents.test_generator import GeneratedTestSuite, generate_pytest_tests_from_plan
from src.agents.test_planner import TestPlan, plan_tests
from src.tools.repo_scanner import RepositoryScanResult


@dataclass(frozen=True)
class UnitTestReport:
    project_path: str
    applied: bool
    test_file_path: str
    test_plan: TestPlan
    suite: GeneratedTestSuite
    security_check: SecurityCheckResult

    @property
    def planned_test_count(self) -> int:
        return self.test_plan.item_count

    @property
    def generated_test_count(self) -> int:
        return self.suite.test_count


def generate_missing_unit_tests(
    project_path: str | Path,
    scan: RepositoryScanResult,
    apply_changes: bool = False,
    test_file_path: str | Path = "tests/test_software_engineer_generated.py",
    max_functions: int = 8,
) -> UnitTestReport:
    root = Path(project_path).resolve()
    existing_test_text = _collect_existing_test_text(root, scan.test_files)
    full_plan = plan_tests(root, scan, max_functions=max_functions)
    missing_plan = TestPlan(
        items=[
            item
            for item in full_plan.items
            if not _has_existing_test_reference(item.function_name, existing_test_text)
        ]
    )
    suite = generate_pytest_tests_from_plan(missing_plan)
    security_check = check_generated_test_code(suite.content)
    if not security_check.passed:
        raise ValueError("Generated unit tests failed security check.")

    target_file = _resolve_project_file(root, test_file_path)
    if apply_changes:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(suite.content, encoding="utf-8")

    return UnitTestReport(
        project_path=str(root),
        applied=apply_changes,
        test_file_path=target_file.relative_to(root).as_posix(),
        test_plan=missing_plan,
        suite=suite,
        security_check=security_check,
    )


def format_unit_test_report(report: UnitTestReport) -> str:
    lines = [
        "[Software Engineer Agent Unit Test Writer]",
        "",
        f"Project: {report.project_path}",
        f"Applied: {report.applied}",
        f"Test File: {report.test_file_path}",
        f"Planned Test Cases: {report.planned_test_count}",
        f"Generated Test Cases: {report.generated_test_count}",
        f"Security Check: {_security_check_status(report.security_check)}",
    ]

    if report.suite.covered_functions:
        lines.append("")
        lines.append("Covered Functions:")
        lines.extend(f"- {function}" for function in report.suite.covered_functions)

    return "\n".join(lines)


def _collect_existing_test_text(root: Path, test_files: list[str]) -> str:
    chunks: list[str] = []
    for relative_file in test_files:
        path = root / relative_file
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _has_existing_test_reference(function_name: str, test_text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(function_name)}\b", test_text))


def _resolve_project_file(root: Path, test_file_path: str | Path) -> Path:
    candidate = Path(test_file_path)
    target = candidate if candidate.is_absolute() else root / candidate
    resolved = target.resolve()
    if not _is_relative_to(resolved, root):
        raise ValueError("Test file path must stay inside the target project.")
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _security_check_status(result: SecurityCheckResult) -> str:
    if result.passed:
        return "passed"
    return f"failed ({result.violation_count} violation(s))"
