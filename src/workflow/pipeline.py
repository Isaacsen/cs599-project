from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.sandbox.local_executor import TestExecutionResult, run_pytest
from src.tools.repo_scanner import RepositoryScanResult, scan_repository


@dataclass(frozen=True)
class PipelineReport:
    scan: RepositoryScanResult
    execution: TestExecutionResult


def run_pipeline(project_path: str | Path, timeout_seconds: int = 30) -> PipelineReport:
    scan = scan_repository(project_path)
    execution = run_pytest(project_path, timeout_seconds=timeout_seconds)
    return PipelineReport(scan=scan, execution=execution)


def format_report(report: PipelineReport) -> str:
    status = "PASSED" if report.execution.passed else "FAILED"
    lines = [
        "[TestGuard Agent MVP]",
        "",
        f"Project: {report.scan.project_path}",
        f"Language: {report.scan.language}",
        f"Test Framework: {report.scan.test_framework}",
        f"Source files: {len(report.scan.source_files)}",
        f"Test files: {len(report.scan.test_files)}",
        "",
        f"Test Result: {status}",
        f"Exit Code: {report.execution.exit_code}",
        f"Timed Out: {report.execution.timed_out}",
        f"Duration: {report.execution.duration_seconds:.2f}s",
    ]

    if report.execution.stdout.strip():
        lines.extend(["", "pytest stdout:", report.execution.stdout.rstrip()])
    if report.execution.stderr.strip():
        lines.extend(["", "pytest stderr:", report.execution.stderr.rstrip()])

    return "\n".join(lines)
