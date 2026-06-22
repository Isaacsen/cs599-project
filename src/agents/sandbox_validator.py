from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.agents.failure_diagnoser import FailureDiagnosis, diagnose_failure
from src.agents.llm_test_generator import LLMTestGenerationReport
from src.agents.result_analyzer import PytestSummary, analyze_pytest_result
from src.agents.security_checker import SecurityCheckResult
from src.agents.unit_test_writer import UnitTestReport
from src.sandbox.docker_executor import run_pytest_in_docker
from src.sandbox.local_executor import TestExecutionResult, run_pytest
from src.sandbox.policy import SandboxPolicy
from src.tools.repo_scanner import IGNORED_DIRS


@dataclass(frozen=True)
class SandboxValidationReport:
    project_path: str
    status: str
    executor: str
    generated_test_files: list[str]
    execution: TestExecutionResult
    analysis: PytestSummary
    diagnosis: FailureDiagnosis
    security_checks: list[SecurityCheckResult]

    @property
    def passed(self) -> bool:
        return self.execution.passed


def validate_generated_tests_in_sandbox(
    project_path: str | Path,
    unit_tests: UnitTestReport | None = None,
    llm_tests: LLMTestGenerationReport | None = None,
    executor: str = "docker",
    docker_image: str = "software-engineer-agent-python:latest",
    timeout_seconds: int = 30,
) -> SandboxValidationReport:
    root = Path(project_path).resolve()
    try:
        with tempfile.TemporaryDirectory(prefix="software-engineer-agent-agent-") as temp_dir:
            workspace = _copy_project(root, temp_dir)
            generated_files = _write_generated_tests(workspace, unit_tests, llm_tests)
            execution = _run_executor(workspace, executor, docker_image, timeout_seconds)
    except Exception as exc:
        execution = TestExecutionResult(
            passed=False,
            exit_code=None,
            stdout="",
            stderr=f"{type(exc).__name__}: {exc}",
            duration_seconds=0.0,
            timed_out=False,
            executor=executor,
        )
        analysis = PytestSummary(total=0, conclusion="error", errors=1)
        diagnosis = FailureDiagnosis(
            status="needs_attention",
            failure_types=["sandbox_error"],
            key_findings=[execution.stderr],
            suggestions=["Inspect sandbox configuration, Docker availability, and target project path."],
        )
        return SandboxValidationReport(
            project_path=str(root),
            status="failed",
            executor=executor,
            generated_test_files=[],
            execution=execution,
            analysis=analysis,
            diagnosis=diagnosis,
            security_checks=[],
        )

    analysis = analyze_pytest_result(execution)
    diagnosis = diagnose_failure(execution, analysis)
    security_checks = [
        result
        for result in (
            unit_tests.security_check if unit_tests else None,
            llm_tests.security_check if llm_tests else None,
        )
        if result is not None
    ]
    return SandboxValidationReport(
        project_path=str(root),
        status="passed" if execution.passed else "failed",
        executor=executor,
        generated_test_files=generated_files,
        execution=execution,
        analysis=analysis,
        diagnosis=diagnosis,
        security_checks=security_checks,
    )


def _copy_project(root: Path, temp_dir: str | Path) -> Path:
    destination = Path(temp_dir).resolve() / "project"
    shutil.copytree(root, destination, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
    return destination


def _write_generated_tests(
    workspace: Path,
    unit_tests: UnitTestReport | None,
    llm_tests: LLMTestGenerationReport | None,
) -> list[str]:
    generated_files: list[str] = []
    for report in (unit_tests, llm_tests):
        if report is None or report.suite is None:
            continue
        relative_path = Path(report.test_file_path)
        target = workspace / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report.suite.content, encoding="utf-8")
        generated_files.append(relative_path.as_posix())
    return generated_files


def _run_executor(
    workspace: Path,
    executor: str,
    docker_image: str,
    timeout_seconds: int,
) -> TestExecutionResult:
    if executor == "local":
        return run_pytest(workspace, timeout_seconds=timeout_seconds)
    if executor == "docker":
        policy = SandboxPolicy(image=docker_image, timeout_seconds=timeout_seconds)
        return run_pytest_in_docker(workspace, policy=policy)
    raise ValueError(f"Unsupported sandbox executor: {executor}")
