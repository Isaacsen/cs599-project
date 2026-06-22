from __future__ import annotations

import argparse
import os
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
    parser = argparse.ArgumentParser(description="Run Software Engineer Agent software engineer LangGraph workflow.")
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
        "--apply-tests",
        action="store_true",
        help="Write generated pytest tests to the target project. Omit for dry-run planning.",
    )
    parser.add_argument(
        "--apply-fixes",
        action="store_true",
        help="Apply LLM code fixes to source files. Omit to keep fixes as dry-run suggestions.",
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
        default="software-engineer-agent-python:latest",
        help="Docker image used by sandbox validation.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for sandbox validation.",
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=None,
        help="Timeout in seconds for each LLM request. Defaults to LLM_TIMEOUT_SECONDS or 60.",
    )
    parser.add_argument(
        "--llm-retries",
        type=int,
        default=None,
        help="Number of retry attempts for each LLM request. Defaults to LLM_MAX_RETRIES or 1.",
    )
    parser.add_argument(
        "--repair-iterations",
        type=int,
        default=3,
        help="Maximum repair-loop retries after sandbox failures.",
    )
    parser.add_argument(
        "--llm-test-file",
        default="tests/test_software_engineer_llm_generated.py",
        help="Project-relative path for generated LLM tests when --apply-tests is enabled.",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=8,
        help="Maximum public functions to consider for generated tests.",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable live per-agent progress output.",
    )
    parser.add_argument(
        "--stream-llm-tokens",
        action="store_true",
        help="Deprecated: token-level LLM streaming is enabled by default.",
    )
    parser.add_argument(
        "--no-llm-token-stream",
        action="store_true",
        help="Disable token-level LLM streaming output.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.llm_timeout is not None:
            os.environ["LLM_TIMEOUT_SECONDS"] = str(args.llm_timeout)
        if args.llm_retries is not None:
            os.environ["LLM_MAX_RETRIES"] = str(args.llm_retries)
        if not args.no_llm_token_stream:
            os.environ["LLM_STREAM_STDOUT"] = "1"
            print(
                "[llm-stream-warning] token-level output may include source snippets or model-generated code.",
                flush=True,
            )
        report = run_software_engineer_graph(
            args.project_path,
            apply_fixes=args.apply_fixes,
            apply_tests=args.apply_tests,
            run_sandbox=args.run_sandbox,
            sandbox_executor=args.sandbox_executor,
            docker_image=args.docker_image,
            timeout_seconds=args.timeout,
            repair_iterations=args.repair_iterations,
            llm_test_file_path=args.llm_test_file,
            max_functions=args.max_functions,
            progress_callback=None if args.no_stream else _print_agent_progress,
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


def _print_agent_progress(node: str, state: dict) -> None:
    is_start = node.endswith(":start")
    base_node = node.removesuffix(":start")
    labels = {
        "scan": "Repo scan",
        "llm_review": "LLM review",
        "llm_fix_plan": "LLM fix planner",
        "llm_fix": "LLM code fixer",
        "llm_tests": "LLM test writer",
        "sandbox_validate": "Sandbox pytest",
        "repair_loop": "Repair loop",
        "coverage_feedback": "Coverage feedback",
        "finish": "Finish",
    }
    if is_start:
        print(f"[agent-stream] {labels.get(base_node, base_node)}: starting", flush=True)
        return
    print(f"[agent-stream] {labels.get(base_node, base_node)}: {_progress_status(base_node, state)}", flush=True)


def _progress_status(node: str, state: dict) -> str:
    if node == "scan" and state.get("scan"):
        scan = state["scan"]
        return f"{scan.status}, {len(scan.source_files)} source file(s)"
    if node == "llm_review" and state.get("llm_review"):
        return f"{state['llm_review'].finding_count} finding(s)"
    if node == "llm_fix_plan" and state.get("llm_fix_plan"):
        plan = state["llm_fix_plan"]
        return f"{plan.target_count} target(s), remaining={plan.remaining_count}, {plan.status}"
    if node == "llm_fix" and state.get("llm_fix"):
        report = state["llm_fix"]
        return f"{report.fix_count} fix(es), {report.status}"
    if node == "llm_tests" and state.get("llm_tests"):
        return f"{state['llm_tests'].generated_test_count} test(s), {state['llm_tests'].status}"
    if node == "sandbox_validate" and state.get("sandbox_validation"):
        report = state["sandbox_validation"]
        return f"{report.status}, {report.analysis.passed}/{report.analysis.total} passed"
    if node == "repair_loop" and state.get("repair_loop"):
        report = state["repair_loop"]
        return f"{report.status}, next={report.next_step}"
    if node == "coverage_feedback" and state.get("coverage_feedback"):
        return f"{state['coverage_feedback'].coverage_ratio:.0%}"
    if node == "finish":
        return state.get("status", "unknown")
    return "completed"


if __name__ == "__main__":
    raise SystemExit(main())
