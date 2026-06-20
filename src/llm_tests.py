from __future__ import annotations

import argparse
import sys

from src.agents.llm_test_generator import format_llm_test_generation_report, generate_llm_pytest_tests
from src.tools.llm_test_writer import write_llm_test_report
from src.tools.repo_scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard LLM test generator agent.")
    parser.add_argument("project_path", help="Path to the Python project to analyze.")
    parser.add_argument(
        "--output",
        default="docs/runs/llm_tests.json",
        help="Path to write the JSON LLM test generation report.",
    )
    parser.add_argument(
        "--test-file",
        default="tests/test_testguard_llm_generated.py",
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
        report = generate_llm_pytest_tests(
            args.project_path,
            scan,
            apply_changes=args.apply,
            test_file_path=args.test_file,
            max_functions=args.max_functions,
        )
        output_path = write_llm_test_report(report, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_llm_test_generation_report(report))
    print(f"\nLLM Test Report: {output_path}")
    return 0 if report.status != "security_failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
