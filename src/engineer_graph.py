from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.tools.software_engineer_graph_writer import write_software_engineer_graph_result
from src.workflow.software_engineer_graph import (
    format_software_engineer_graph_result,
    run_software_engineer_graph,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard software engineer LangGraph workflow.")
    parser.add_argument("project_path", help="Path to the Python project to inspect.")
    parser.add_argument(
        "--output",
        default="docs/runs/software_engineer_graph.json",
        help="Path to write the JSON LangGraph workflow report.",
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
        "--use-llm-tests",
        action="store_true",
        help="Run the LLM Test Generator node after unit-test generation.",
    )
    parser.add_argument(
        "--mock-llm-response",
        help="Optional file containing an LLM response for offline graph demos.",
    )
    parser.add_argument(
        "--test-file",
        default="tests/test_testguard_generated.py",
        help="Project-relative path for generated unit tests when --apply-tests is enabled.",
    )
    parser.add_argument(
        "--llm-test-file",
        default="tests/test_testguard_llm_generated.py",
        help="Project-relative path for generated LLM tests when --apply-tests is enabled.",
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
        mock_response = _read_optional_file(args.mock_llm_response)
        result = run_software_engineer_graph(
            args.project_path,
            apply_fixes=args.apply_fixes,
            apply_tests=args.apply_tests,
            use_llm_tests=args.use_llm_tests,
            test_file_path=args.test_file,
            llm_test_file_path=args.llm_test_file,
            max_functions=args.max_functions,
            mock_llm_response=mock_response,
        )
        output_path = write_software_engineer_graph_result(result, args.output)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_software_engineer_graph_result(result))
    print(f"\nSoftware Engineer Graph Report: {output_path}")
    return 0


def _read_optional_file(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
