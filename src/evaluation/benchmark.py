from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.tools.software_engineer_graph_writer import software_engineer_graph_result_to_dict
from src.workflow.software_engineer_graph import SoftwareEngineerGraphResult, run_software_engineer_graph


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    project_path: str
    generate_tests: bool = True


@dataclass(frozen=True)
class BenchmarkResult:
    case: BenchmarkCase
    report: SoftwareEngineerGraphResult

    @property
    def passed(self) -> bool:
        sandbox = self.report.state.get("sandbox_validation")
        if sandbox is None:
            return self.report.state.get("status") == "completed"
        return sandbox.passed


@dataclass(frozen=True)
class BenchmarkSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    total_pytest_cases: int
    generated_test_cases: int
    planned_test_cases: int
    total_duration_seconds: float


DEFAULT_BENCHMARK_CASES = [
    BenchmarkCase(
        name="sample_python_project",
        project_path="examples/sample_python_project",
        generate_tests=True,
    )
]


def run_benchmark(
    cases: list[BenchmarkCase] | None = None,
    timeout_seconds: int = 30,
    executor: str = "local",
    docker_image: str = "software-engineer-agent-python:latest",
) -> tuple[BenchmarkSummary, list[BenchmarkResult]]:
    active_cases = cases or DEFAULT_BENCHMARK_CASES
    results: list[BenchmarkResult] = []

    for case in active_cases:
        report = run_software_engineer_graph(
            case.project_path,
            timeout_seconds=timeout_seconds,
            run_sandbox=True,
            sandbox_executor=executor,
            docker_image=docker_image,
            apply_tests=False,
        )
        results.append(BenchmarkResult(case=case, report=report))

    return summarize_results(results), results


def summarize_results(results: list[BenchmarkResult]) -> BenchmarkSummary:
    total_cases = len(results)
    passed_cases = sum(1 for result in results if result.passed)
    failed_cases = total_cases - passed_cases
    total_pytest_cases = sum(_sandbox_total(result.report) for result in results)
    generated_test_cases = sum(result.report.generated_llm_test_count for result in results)
    planned_test_cases = sum(_planned_test_count(result.report) for result in results)
    total_duration_seconds = sum(_sandbox_duration(result.report) for result in results)
    pass_rate = passed_cases / total_cases if total_cases else 0.0

    return BenchmarkSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        pass_rate=pass_rate,
        total_pytest_cases=total_pytest_cases,
        generated_test_cases=generated_test_cases,
        planned_test_cases=planned_test_cases,
        total_duration_seconds=total_duration_seconds,
    )


def benchmark_to_dict(summary: BenchmarkSummary, results: list[BenchmarkResult]) -> dict[str, Any]:
    return {
        "summary": asdict(summary),
        "results": [
            {
                "case": asdict(result.case),
                "report": software_engineer_graph_result_to_dict(result.report),
            }
            for result in results
        ],
    }


def write_benchmark_report(
    summary: BenchmarkSummary,
    results: list[BenchmarkResult],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(benchmark_to_dict(summary, results), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _sandbox_total(report: SoftwareEngineerGraphResult) -> int:
    sandbox = report.state.get("sandbox_validation")
    if sandbox is None:
        return 0
    return sandbox.analysis.total


def _sandbox_duration(report: SoftwareEngineerGraphResult) -> float:
    sandbox = report.state.get("sandbox_validation")
    if sandbox is None:
        return 0.0
    return sandbox.execution.duration_seconds


def _planned_test_count(report: SoftwareEngineerGraphResult) -> int:
    llm_tests = report.state.get("llm_tests")
    if llm_tests is None:
        return 0
    return llm_tests.test_plan.item_count


def format_benchmark_summary(summary: BenchmarkSummary) -> str:
    return "\n".join(
        [
            "[Software Engineer Agent Benchmark]",
            "",
            f"Total Cases: {summary.total_cases}",
            f"Passed Cases: {summary.passed_cases}",
            f"Failed Cases: {summary.failed_cases}",
            f"Pass Rate: {summary.pass_rate:.2%}",
            f"Total Pytest Cases: {summary.total_pytest_cases}",
            f"Planned Test Cases: {summary.planned_test_cases}",
            f"Generated Test Cases: {summary.generated_test_cases}",
            f"Total Duration: {summary.total_duration_seconds:.2f}s",
        ]
    )
