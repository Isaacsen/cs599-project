from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.bug_fixer import FixPlan, fix_repository
from src.agents.code_reviewer import ReviewReport, review_repository
from src.agents.unit_test_writer import UnitTestReport, generate_missing_unit_tests
from src.tools.repo_scanner import RepositoryScanResult, scan_repository


@dataclass(frozen=True)
class SoftwareEngineerReport:
    project_path: str
    scan: RepositoryScanResult
    review: ReviewReport
    fix_plan: FixPlan
    unit_tests: UnitTestReport

    @property
    def finding_count(self) -> int:
        return self.review.finding_count

    @property
    def fix_edit_count(self) -> int:
        return self.fix_plan.edit_count

    @property
    def generated_test_count(self) -> int:
        return self.unit_tests.generated_test_count


def run_software_engineer_agent(
    project_path: str | Path,
    apply_fixes: bool = False,
    apply_tests: bool = False,
    test_file_path: str | Path = "tests/test_testguard_generated.py",
    max_functions: int = 8,
) -> SoftwareEngineerReport:
    root = Path(project_path).resolve()
    scan = scan_repository(root)
    review = review_repository(root, scan)
    fix_plan = fix_repository(root, scan, apply_changes=apply_fixes)

    test_scan = scan_repository(root) if apply_fixes else scan
    unit_tests = generate_missing_unit_tests(
        root,
        test_scan,
        apply_changes=apply_tests,
        test_file_path=test_file_path,
        max_functions=max_functions,
    )

    return SoftwareEngineerReport(
        project_path=str(root),
        scan=scan,
        review=review,
        fix_plan=fix_plan,
        unit_tests=unit_tests,
    )


def format_software_engineer_report(report: SoftwareEngineerReport) -> str:
    lines = [
        "[TestGuard Software Engineer Agent]",
        "",
        f"Project: {report.project_path}",
        f"Source files: {len(report.scan.source_files)}",
        f"Test files: {len(report.scan.test_files)}",
        "",
        f"Review Findings: {report.finding_count}",
        f"Review High: {report.review.high_count}",
        f"Review Medium: {report.review.medium_count}",
        f"Review Low: {report.review.low_count}",
        "",
        f"Fix Applied: {report.fix_plan.applied}",
        f"Fix Edits: {report.fix_edit_count}",
        f"Fix Files Changed: {report.fix_plan.files_changed}",
        "",
        f"Unit Tests Applied: {report.unit_tests.applied}",
        f"Unit Test File: {report.unit_tests.test_file_path}",
        f"Generated Test Cases: {report.generated_test_count}",
        f"Unit Test Security: {_unit_test_security_status(report)}",
    ]
    return "\n".join(lines)


def _unit_test_security_status(report: SoftwareEngineerReport) -> str:
    result = report.unit_tests.security_check
    if result.passed:
        return "passed"
    return f"failed ({result.violation_count} violation(s))"
