from __future__ import annotations

import argparse
import sys

from src.tools.report_writer import write_json_report
from src.workflow.pipeline import format_report, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard Agent MVP pipeline.")
    parser.add_argument("project_path", help="Path to the Python project to scan and test.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for pytest execution.",
    )
    parser.add_argument(
        "--executor",
        choices=("local", "docker"),
        default="local",
        help="Execution backend for pytest.",
    )
    parser.add_argument(
        "--docker-image",
        default="testguard-python:latest",
        help="Docker image used when --executor docker is selected.",
    )
    parser.add_argument(
        "--generate-tests",
        action="store_true",
        help="Generate pytest tests before executing the selected backend.",
    )
    parser.add_argument(
        "--report-json",
        help="Optional path to write a structured JSON run report.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        report = run_pipeline(
            args.project_path,
            timeout_seconds=args.timeout,
            executor=args.executor,
            docker_image=args.docker_image,
            generate_tests=args.generate_tests,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_report(report))
    if args.report_json:
        output_path = write_json_report(report, args.report_json)
        print(f"\nJSON Report: {output_path}")
    return 0 if report.execution.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
