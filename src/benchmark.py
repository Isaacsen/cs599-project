from __future__ import annotations

import argparse
import sys

from src.evaluation.benchmark import (
    DEFAULT_BENCHMARK_CASES,
    BenchmarkCase,
    format_benchmark_summary,
    run_benchmark,
    write_benchmark_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard benchmark cases.")
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="Benchmark case in name=project_path format. Can be repeated.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for each pytest execution.",
    )
    parser.add_argument(
        "--executor",
        choices=("local", "docker"),
        default="local",
        help="Execution backend for each benchmark case.",
    )
    parser.add_argument(
        "--docker-image",
        default="testguard-python:latest",
        help="Docker image used when --executor docker is selected.",
    )
    parser.add_argument(
        "--output",
        default="docs/runs/benchmark.json",
        help="Path to write benchmark JSON output.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        cases = _parse_cases(args.cases)
        summary, results = run_benchmark(
            cases=cases,
            timeout_seconds=args.timeout,
            executor=args.executor,
            docker_image=args.docker_image,
        )
        output_path = write_benchmark_report(summary, results, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_benchmark_summary(summary))
    print(f"\nBenchmark Report: {output_path}")
    return 0 if summary.failed_cases == 0 else 1


def _parse_cases(raw_cases: list[str] | None) -> list[BenchmarkCase]:
    if not raw_cases:
        return DEFAULT_BENCHMARK_CASES

    cases: list[BenchmarkCase] = []
    for raw_case in raw_cases:
        if "=" not in raw_case:
            raise ValueError(f"Invalid benchmark case: {raw_case}. Expected name=project_path.")
        name, project_path = raw_case.split("=", 1)
        if not name or not project_path:
            raise ValueError(f"Invalid benchmark case: {raw_case}. Expected name=project_path.")
        cases.append(BenchmarkCase(name=name, project_path=project_path, generate_tests=True))
    return cases


if __name__ == "__main__":
    raise SystemExit(main())
