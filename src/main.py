from __future__ import annotations

import argparse
import sys

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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        report = run_pipeline(args.project_path, timeout_seconds=args.timeout)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_report(report))
    return 0 if report.execution.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
