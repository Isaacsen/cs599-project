from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.tools.report_writer import report_to_dict
from src.workflow.pipeline import PipelineReport, run_pipeline


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    project_path: str
    generate_tests: bool = True


@dataclass(frozen=True)
class BenchmarkResult:
    case: BenchmarkCase
    report: PipelineReport

    @property
    def passed(self) -> bool:
        return self.report.execution.passed


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
        report = run_pipeline(
            case.project_path,
            timeout_seconds=timeout_seconds,
            executor=executor,
            docker_image=docker_image,
            generate_tests=case.generate_tests,
        )
        results.append(BenchmarkResult(case=case, report=report))

    return summarize_results(results), results


def summarize_results(results: list[BenchmarkResult]) -> BenchmarkSummary:
    total_cases = len(results)
    passed_cases = sum(1 for result in results if result.passed)
    failed_cases = total_cases - passed_cases
    total_pytest_cases = sum(result.report.analysis.total for result in results)
    generated_test_cases = sum(
        result.report.generated_suite.test_count
        for result in results
        if result.report.generated_suite is not None
    )
    planned_test_cases = sum(
        result.report.test_plan.item_count
        for result in results
        if result.report.test_plan is not None
    )
    total_duration_seconds = sum(result.report.execution.duration_seconds for result in results)
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
                "report": report_to_dict(result.report),
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
