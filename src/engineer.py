from __future__ import annotations

import argparse
import sys

from src.tools.software_engineer_graph_writer import (
    write_software_engineer_graph_result,
    write_software_engineer_markdown,
)
from src.workflow.software_engineer_graph import (
    format_software_engineer_graph_result,
    run_software_engineer_graph,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TestGuard software engineer LangGraph workflow.")
    parser.add_argument("project_path", help="Path to the Python project to inspect.")
    parser.add_argument(
        "--output",
        default="docs/runs/software_engineer.json",
        help="Path to write the JSON software engineer graph report.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/runs/software_engineer.md",
        help="Path to write the human-readable Markdown software engineer report.",
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
        "--use-llm-review",
        action="store_true",
        help="Run the LLM Code Review node after rule-based review.",
    )
    parser.add_argument(
        "--run-sandbox",
        action="store_true",
        help="Run generated tests through the sandbox validation node.",
    )
    parser.add_argument(
        "--sandbox-executor",
        choices=("local", "docker"),
        default="docker",
        help="Sandbox validation backend.",
    )
    parser.add_argument(
        "--docker-image",
        default="testguard-python:latest",
        help="Docker image used by sandbox validation.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for sandbox validation.",
    )
    parser.add_argument(
        "--repair-iterations",
        type=int,
        default=1,
        help="Maximum repair-loop iterations to plan.",
    )
    parser.add_argument(
        "--test-file",
        default="tests/test_testguard_generated.py",
        help="Project-relative path for generated pytest tests when --apply-tests is enabled.",
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
        report = run_software_engineer_graph(
            args.project_path,
            apply_fixes=args.apply_fixes,
            apply_tests=args.apply_tests,
            use_llm_review=args.use_llm_review,
            use_llm_tests=args.use_llm_tests,
            run_sandbox=args.run_sandbox,
            sandbox_executor=args.sandbox_executor,
            docker_image=args.docker_image,
            timeout_seconds=args.timeout,
            repair_iterations=args.repair_iterations,
            test_file_path=args.test_file,
            llm_test_file_path=args.llm_test_file,
            max_functions=args.max_functions,
        )
        output_path = write_software_engineer_graph_result(report, args.output)
        markdown_path = write_software_engineer_markdown(report, args.output_md)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_software_engineer_graph_result(report))
    print(f"\nSoftware Engineer Report: {output_path}")
    print(f"Readable Report: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
