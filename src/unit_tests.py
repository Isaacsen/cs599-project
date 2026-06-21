from __future__ import annotations

import argparse
import sys

from src.agents.unit_test_writer import format_unit_test_report, generate_missing_unit_tests
from src.tools.repo_scanner import scan_repository
from src.tools.unit_test_writer import write_unit_test_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Software Engineer Agent unit test writer agent.")
    parser.add_argument("project_path", help="Path to the Python project to analyze.")
    parser.add_argument(
        "--output",
        default="docs/runs/unit_tests.json",
        help="Path to write the JSON unit-test generation report.",
    )
    parser.add_argument(
        "--test-file",
        default="tests/test_software_engineer_generated.py",
        help="Project-relative path to write generated pytest tests when --apply is enabled.",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=8,
        help="Maximum public functions to consider for generated tests.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write generated pytest tests to the target project. Omit for dry-run planning.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        scan = scan_repository(args.project_path)
        report = generate_missing_unit_tests(
            args.project_path,
            scan,
            apply_changes=args.apply,
            test_file_path=args.test_file,
            max_functions=args.max_functions,
        )
        output_path = write_unit_test_report(report, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_unit_test_report(report))
    print(f"\nUnit Test Report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
