from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.agents.failure_diagnoser import FailureDiagnosis, diagnose_failure
from src.agents.result_analyzer import PytestSummary, analyze_pytest_result
from src.agents.security_checker import SecurityCheckResult, check_generated_test_code
from src.agents.test_generator import GeneratedTestSuite, generate_pytest_tests_from_plan
from src.agents.test_planner import TestPlan, plan_tests
from src.sandbox.docker_executor import run_pytest_in_docker
from src.sandbox.local_executor import TestExecutionResult, run_pytest
from src.sandbox.policy import SandboxPolicy
from src.tools.repo_scanner import RepositoryScanResult, scan_repository
from src.tools.test_workspace import copy_project_with_generated_tests


@dataclass(frozen=True)
class PipelineReport:
    scan: RepositoryScanResult
    execution: TestExecutionResult
    analysis: PytestSummary
    diagnosis: FailureDiagnosis
    security_check: SecurityCheckResult | None = None
    test_plan: TestPlan | None = None
    generated_suite: GeneratedTestSuite | None = None
    generated_tests_enabled: bool = False


def run_pipeline(
    project_path: str | Path,
    timeout_seconds: int = 30,
    executor: str = "local",
    docker_image: str = "testguard-python:latest",
    generate_tests: bool = False,
) -> PipelineReport:
    scan = scan_repository(project_path)
    test_plan: TestPlan | None = None
    generated_suite: GeneratedTestSuite | None = None
    security_check: SecurityCheckResult | None = None
    execution_project = Path(project_path)

    if generate_tests:
        test_plan = plan_tests(project_path, scan)
        generated_suite = generate_pytest_tests_from_plan(test_plan)
        security_check = check_generated_test_code(generated_suite.content)
        if not security_check.passed:
            raise ValueError("Generated tests failed security check.")
        with tempfile.TemporaryDirectory(prefix="testguard-") as temp_dir:
            execution_project = copy_project_with_generated_tests(project_path, temp_dir, generated_suite)
            execution = _run_executor(
                execution_project,
                timeout_seconds=timeout_seconds,
                executor=executor,
                docker_image=docker_image,
            )
        analysis = analyze_pytest_result(execution)
        diagnosis = diagnose_failure(execution, analysis)
        return PipelineReport(
            scan=scan,
            execution=execution,
            analysis=analysis,
            diagnosis=diagnosis,
            security_check=security_check,
            test_plan=test_plan,
            generated_suite=generated_suite,
            generated_tests_enabled=True,
        )

    execution = _run_executor(
        execution_project,
        timeout_seconds=timeout_seconds,
        executor=executor,
        docker_image=docker_image,
    )
    analysis = analyze_pytest_result(execution)
    diagnosis = diagnose_failure(execution, analysis)
    return PipelineReport(
        scan=scan,
        execution=execution,
        analysis=analysis,
        diagnosis=diagnosis,
        security_check=security_check,
        test_plan=test_plan,
        generated_tests_enabled=False,
    )


def _run_executor(
    project_path: str | Path,
    timeout_seconds: int,
    executor: str,
    docker_image: str,
) -> TestExecutionResult:
    if executor == "local":
        return run_pytest(project_path, timeout_seconds=timeout_seconds)
    if executor == "docker":
        policy = SandboxPolicy(image=docker_image, timeout_seconds=timeout_seconds)
        return run_pytest_in_docker(project_path, policy=policy)
    raise ValueError(f"Unsupported executor: {executor}")


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
        f"Generated Tests: {report.generated_tests_enabled}",
        f"Planned Test Cases: {_planned_test_count(report)}",
        f"Generated Test Cases: {_generated_test_count(report)}",
        f"Security Check: {_security_check_status(report)}",
        f"Executor: {report.execution.executor}",
        f"Test Result: {status}",
        f"Exit Code: {report.execution.exit_code}",
        f"Timed Out: {report.execution.timed_out}",
        f"Duration: {report.execution.duration_seconds:.2f}s",
        "",
        "Pytest Summary:",
        f"  total: {report.analysis.total}",
        f"  passed: {report.analysis.passed}",
        f"  failed: {report.analysis.failed}",
        f"  errors: {report.analysis.errors}",
        f"  skipped: {report.analysis.skipped}",
        f"  warnings: {report.analysis.warnings}",
        f"  conclusion: {report.analysis.conclusion}",
        "",
        "Diagnosis:",
        f"  status: {report.diagnosis.status}",
        f"  failure_types: {', '.join(report.diagnosis.failure_types) if report.diagnosis.failure_types else 'none'}",
    ]

    if report.diagnosis.key_findings:
        lines.append("  key_findings:")
        lines.extend(f"    - {finding}" for finding in report.diagnosis.key_findings)
    if report.diagnosis.suggestions:
        lines.append("  suggestions:")
        lines.extend(f"    - {suggestion}" for suggestion in report.diagnosis.suggestions)

    if report.execution.stdout.strip():
        lines.extend(["", "pytest stdout:", report.execution.stdout.rstrip()])
    if report.execution.stderr.strip():
        lines.extend(["", "pytest stderr:", report.execution.stderr.rstrip()])

    return "\n".join(lines)


def _generated_test_count(report: PipelineReport) -> int:
    if report.generated_suite is None:
        return 0
    return report.generated_suite.test_count


def _planned_test_count(report: PipelineReport) -> int:
    if report.test_plan is None:
        return 0
    return report.test_plan.item_count


def _security_check_status(report: PipelineReport) -> str:
    if report.security_check is None:
        return "not_run"
    if report.security_check.passed:
        return "passed"
    return f"failed ({report.security_check.violation_count} violation(s))"
