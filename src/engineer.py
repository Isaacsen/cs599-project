from __future__ import annotations

import argparse
import sys

from src.agents.software_engineer import format_software_engineer_report, run_software_engineer_agent
from src.tools.software_engineer_writer import write_software_engineer_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard software engineer agent.")
    parser.add_argument("project_path", help="Path to the Python project to inspect.")
    parser.add_argument(
        "--output",
        default="docs/runs/software_engineer.json",
        help="Path to write the JSON software engineer report.",
    )
    parser.add_argument(
        "--apply-fixes",
        action="store_true",
        help="Apply safe bug fixes to the target project. Omit for dry-run planning.",
    )
    parser.add_argument(
        "--apply-tests",
        action="store_true",
        help="Write generated pytest tests to the target project. Omit for dry-run planning.",
    )
    parser.add_argument(
        "--test-file",
        default="tests/test_testguard_generated.py",
        help="Project-relative path for generated pytest tests when --apply-tests is enabled.",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=8,
        help="Maximum public functions to consider for generated tests.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        report = run_software_engineer_agent(
            args.project_path,
            apply_fixes=args.apply_fixes,
            apply_tests=args.apply_tests,
            test_file_path=args.test_file,
            max_functions=args.max_functions,
        )
        output_path = write_software_engineer_report(report, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_software_engineer_report(report))
    print(f"\nSoftware Engineer Report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
