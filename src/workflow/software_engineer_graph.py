from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from src.agents.coverage_feedback import CoverageFeedbackReport, build_coverage_feedback
from src.agents.llm_code_fixer import LLMCodeFixReport, fix_code_with_llm
from src.agents.llm_code_reviewer import LLMCodeReviewReport, review_repository_with_llm
from src.agents.llm_test_generator import LLMTestGenerationReport, generate_llm_pytest_tests
from src.agents.repair_loop import RepairLoopReport, plan_repair_iteration
from src.agents.sandbox_validator import SandboxValidationReport, validate_generated_tests_in_sandbox
from src.tools.repo_scanner import RepositoryScanResult, scan_repository

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    END = "__end__"
    START = "__start__"
    StateGraph = None
    LANGGRAPH_AVAILABLE = False


class SoftwareEngineerGraphState(TypedDict, total=False):
    project_path: str
    apply_fixes: bool
    apply_tests: bool
    run_sandbox: bool
    sandbox_executor: str
    docker_image: str
    timeout_seconds: int
    repair_iterations: int
    llm_test_file_path: str
    max_functions: int
    graph_runtime: str
    status: str
    scan: RepositoryScanResult
    llm_review: LLMCodeReviewReport
    llm_fix: LLMCodeFixReport
    llm_fix_history: list[LLMCodeFixReport]
    llm_tests: LLMTestGenerationReport
    llm_tests_history: list[LLMTestGenerationReport]
    sandbox_validation: SandboxValidationReport
    sandbox_validation_history: list[SandboxValidationReport]
    repair_loop: RepairLoopReport
    repair_history: list[RepairLoopReport]
    repair_iteration: int
    coverage_feedback: CoverageFeedbackReport
    node_trace: list[str]


@dataclass(frozen=True)
class SoftwareEngineerGraphResult:
    state: SoftwareEngineerGraphState

    @property
    def project_path(self) -> str:
        return self.state["project_path"]

    @property
    def graph_runtime(self) -> str:
        return self.state.get("graph_runtime", "langgraph")

    @property
    def node_trace(self) -> list[str]:
        return self.state.get("node_trace", [])

    @property
    def generated_llm_test_count(self) -> int:
        llm_tests = self.state.get("llm_tests")
        return llm_tests.generated_test_count if llm_tests else 0


def run_software_engineer_graph(
    project_path: str | Path,
    apply_fixes: bool = False,
    apply_tests: bool = False,
    run_sandbox: bool = False,
    sandbox_executor: str = "docker",
    docker_image: str = "software-engineer-agent-python:latest",
    timeout_seconds: int = 30,
    repair_iterations: int = 3,
    llm_test_file_path: str | Path = "tests/test_software_engineer_llm_generated.py",
    max_functions: int = 8,
) -> SoftwareEngineerGraphResult:
    initial_state: SoftwareEngineerGraphState = {
        "project_path": str(Path(project_path).resolve()),
        "apply_fixes": apply_fixes,
        "apply_tests": apply_tests,
        "run_sandbox": run_sandbox,
        "sandbox_executor": sandbox_executor,
        "docker_image": docker_image,
        "timeout_seconds": timeout_seconds,
        "repair_iterations": repair_iterations,
        "repair_iteration": 0,
        "llm_test_file_path": str(llm_test_file_path),
        "max_functions": max_functions,
        "node_trace": [],
    }

    if LANGGRAPH_AVAILABLE:
        graph = build_software_engineer_graph()
        final_state = graph.invoke(initial_state)
    else:
        final_state = _run_fallback_graph(initial_state)
    return SoftwareEngineerGraphResult(state=final_state)


def build_software_engineer_graph() -> Any:
    if StateGraph is None:
        raise RuntimeError("langgraph is not installed.")

    graph = StateGraph(SoftwareEngineerGraphState)
    graph.add_node("scan", scan_node)
    graph.add_node("llm_review", llm_review_node)
    graph.add_node("llm_fix", llm_fix_node)
    graph.add_node("llm_tests", llm_tests_node)
    graph.add_node("sandbox_validate", sandbox_validate_node)
    graph.add_node("repair_loop", repair_loop_node)
    graph.add_node("coverage_feedback", coverage_feedback_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "scan")
    graph.add_edge("scan", "llm_review")
    graph.add_edge("llm_review", "llm_fix")
    graph.add_edge("llm_fix", "llm_tests")
    graph.add_conditional_edges(
        "llm_tests",
        _route_after_generated_tests,
        {
            "sandbox_validate": "sandbox_validate",
            "coverage_feedback": "coverage_feedback",
        },
    )
    graph.add_edge("sandbox_validate", "repair_loop")
    graph.add_conditional_edges(
        "repair_loop",
        _route_after_repair_loop,
        {
            "llm_fix": "llm_fix",
            "llm_tests": "llm_tests",
            "coverage_feedback": "coverage_feedback",
        },
    )
    graph.add_edge("coverage_feedback", "finish")
    graph.add_edge("finish", END)
    return graph.compile()


def scan_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    scan = scan_repository(state["project_path"])
    return {
        "scan": scan,
        "graph_runtime": "langgraph" if LANGGRAPH_AVAILABLE else "fallback",
        "node_trace": [*state.get("node_trace", []), "scan"],
    }


def llm_review_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    llm_review = review_repository_with_llm(state["project_path"], state["scan"])
    return {
        "llm_review": llm_review,
        "node_trace": [*state.get("node_trace", []), "llm_review"],
    }


def llm_fix_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    repair_loop = state.get("repair_loop")
    llm_fix = fix_code_with_llm(
        state["project_path"],
        state["scan"],
        llm_review=state.get("llm_review"),
        sandbox_validation=state.get("sandbox_validation"),
        repair_actions=repair_loop.actions if repair_loop else [],
        apply_changes=state.get("apply_fixes", False),
    )
    updates: SoftwareEngineerGraphState = {
        "llm_fix": llm_fix,
        "llm_fix_history": [*state.get("llm_fix_history", []), llm_fix],
        "node_trace": [*state.get("node_trace", []), "llm_fix"],
    }
    if llm_fix.applied:
        updates["scan"] = scan_repository(state["project_path"])
    return updates


def llm_tests_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    llm_tests = generate_llm_pytest_tests(
        state["project_path"],
        state["scan"],
        apply_changes=state.get("apply_tests", False),
        test_file_path=state.get("llm_test_file_path", "tests/test_software_engineer_llm_generated.py"),
        max_functions=state.get("max_functions", 8),
    )
    return {
        "llm_tests": llm_tests,
        "llm_tests_history": [*state.get("llm_tests_history", []), llm_tests],
        "node_trace": [*state.get("node_trace", []), "llm_tests"],
    }


def sandbox_validate_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    sandbox_validation = validate_generated_tests_in_sandbox(
        state["project_path"],
        llm_tests=state.get("llm_tests"),
        executor=state.get("sandbox_executor", "docker"),
        docker_image=state.get("docker_image", "software-engineer-agent-python:latest"),
        timeout_seconds=state.get("timeout_seconds", 30),
    )
    return {
        "sandbox_validation": sandbox_validation,
        "sandbox_validation_history": [*state.get("sandbox_validation_history", []), sandbox_validation],
        "node_trace": [*state.get("node_trace", []), "sandbox_validate"],
    }


def repair_loop_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    repair_loop = plan_repair_iteration(
        state.get("sandbox_validation"),
        current_iteration=state.get("repair_iteration", 0),
        max_iterations=state.get("repair_iterations", 3),
    )
    return {
        "repair_loop": repair_loop,
        "repair_history": [*state.get("repair_history", []), repair_loop],
        "repair_iteration": repair_loop.iteration,
        "node_trace": [*state.get("node_trace", []), "repair_loop"],
    }


def coverage_feedback_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    coverage_feedback = build_coverage_feedback(
        state["project_path"],
        state["scan"],
        llm_tests=state.get("llm_tests"),
    )
    return {
        "coverage_feedback": coverage_feedback,
        "node_trace": [*state.get("node_trace", []), "coverage_feedback"],
    }


def finish_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    return {
        "status": "completed",
        "node_trace": [*state.get("node_trace", []), "finish"],
    }


def format_software_engineer_graph_result(result: SoftwareEngineerGraphResult) -> str:
    state = result.state
    lines = [
        "[Software Engineer Agent LangGraph]",
        "",
        "Run Summary",
        f"  Project: {result.project_path}",
        f"  Status: {state.get('status', 'unknown')}",
        f"  Runtime: {result.graph_runtime}",
        "",
        "Agent Timeline",
        *_format_timeline(state, result.node_trace),
        "",
        "Outcome",
        f"  LLM Review Findings: {_llm_review_count(state)}",
        f"  LLM Fixes Planned: {_llm_fix_count(state)}",
        f"  Generated LLM Tests: {result.generated_llm_test_count}",
        f"  Sandbox Validation: {_sandbox_status(state)}",
        f"  Coverage Feedback: {_coverage_status(state)}",
        "",
        "Highlights",
        *_format_highlights(state),
    ]
    return "\n".join(lines)


def _format_timeline(state: SoftwareEngineerGraphState, node_trace: list[str]) -> list[str]:
    labels = {
        "scan": "Repo scan",
        "llm_review": "LLM code review",
        "llm_fix": "LLM code fixer",
        "llm_tests": "LLM test writer",
        "sandbox_validate": "Sandbox pytest",
        "repair_loop": "Repair loop",
        "coverage_feedback": "Coverage feedback",
        "finish": "Finish",
    }
    occurrences: dict[str, int] = {}
    lines: list[str] = []
    for index, node in enumerate(node_trace, start=1):
        occurrences[node] = occurrences.get(node, 0) + 1
        lines.append(f"  {index:02d}. {labels.get(node, node)} - {_node_status(state, node, occurrences[node])}")
    return lines


def _node_status(state: SoftwareEngineerGraphState, node: str, occurrence: int = 1) -> str:
    if node == "scan" and "scan" in state:
        return f"{len(state['scan'].source_files)} source file(s)"
    if node == "llm_review" and "llm_review" in state:
        return f"{state['llm_review'].finding_count} finding(s)"
    if node == "llm_fix" and "llm_fix" in state:
        return f"{state['llm_fix'].fix_count} fix(es), {state['llm_fix'].status}"
    if node == "llm_tests" and "llm_tests" in state:
        return f"{state['llm_tests'].generated_test_count} test(s)"
    if node == "sandbox_validate" and "sandbox_validation" in state:
        report = _history_item(state.get("sandbox_validation_history", []), occurrence) or state["sandbox_validation"]
        return f"{report.status}, {report.analysis.passed}/{report.analysis.total} passed"
    if node == "repair_loop" and "repair_loop" in state:
        report = _history_item(state.get("repair_history", []), occurrence) or state["repair_loop"]
        return f"{report.status}, next={report.next_step}"
    if node == "coverage_feedback" and "coverage_feedback" in state:
        return f"{state['coverage_feedback'].coverage_ratio:.0%}"
    if node == "finish":
        return state.get("status", "unknown")
    return "not_run"


def _format_highlights(state: SoftwareEngineerGraphState) -> list[str]:
    highlights: list[str] = []
    llm_review = state.get("llm_review")
    if llm_review and llm_review.findings:
        first = llm_review.findings[0]
        highlights.append(f"  - LLM review: [{first.severity}] {first.message}")
    llm_fix = state.get("llm_fix")
    if llm_fix:
        highlights.append(f"  - LLM fix: {llm_fix.fix_count} fix(es), {llm_fix.status}")
    sandbox = state.get("sandbox_validation")
    if sandbox:
        highlights.append(f"  - Sandbox pytest: {sandbox.analysis.passed}/{sandbox.analysis.total} passed")
    coverage = state.get("coverage_feedback")
    if coverage:
        highlights.append(f"  - Coverage: {coverage.coverage_ratio:.0%}; missing={len(coverage.missing_functions)}")
    repair = state.get("repair_loop")
    if repair and repair.actions:
        highlights.append(f"  - Next action: {repair.actions[0]}")
    if not highlights:
        highlights.append("  - No detailed highlights available.")
    return highlights


def _llm_review_count(state: SoftwareEngineerGraphState) -> int:
    report = state.get("llm_review")
    return report.finding_count if report else 0


def _llm_fix_count(state: SoftwareEngineerGraphState) -> int:
    history = state.get("llm_fix_history", [])
    if history:
        return sum(report.fix_count for report in history)
    report = state.get("llm_fix")
    return report.fix_count if report else 0


def _sandbox_status(state: SoftwareEngineerGraphState) -> str:
    report = state.get("sandbox_validation")
    if report is None:
        return "not_run"
    return report.status


def _coverage_status(state: SoftwareEngineerGraphState) -> str:
    report = state.get("coverage_feedback")
    if report is None:
        return "not_run"
    return f"{report.coverage_ratio:.0%}"


def _route_after_repair_loop(state: SoftwareEngineerGraphState) -> str:
    report = state.get("repair_loop")
    if report is not None and report.next_step == "llm_fix":
        return "llm_fix"
    if report is not None and report.next_step == "llm_tests":
        return "llm_tests"
    return "coverage_feedback"


def _route_after_generated_tests(state: SoftwareEngineerGraphState) -> str:
    if state.get("run_sandbox", False):
        return "sandbox_validate"
    return "coverage_feedback"


def _history_item(items: list[Any], occurrence: int) -> Any | None:
    index = occurrence - 1
    if index < 0 or index >= len(items):
        return None
    return items[index]


def _run_fallback_graph(initial_state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    state: SoftwareEngineerGraphState = dict(initial_state)
    state.update(scan_node(state))
    state.update(llm_review_node(state))
    state.update(llm_fix_node(state))
    state.update(llm_tests_node(state))
    if _route_after_generated_tests(state) == "sandbox_validate":
        state.update(sandbox_validate_node(state))
        state.update(repair_loop_node(state))
        while _route_after_repair_loop(state) in {"llm_fix", "llm_tests"}:
            if _route_after_repair_loop(state) == "llm_fix":
                state.update(llm_fix_node(state))
            state.update(llm_tests_node(state))
            state.update(sandbox_validate_node(state))
            state.update(repair_loop_node(state))
    state.update(coverage_feedback_node(state))
    state.update(finish_node(state))
    state["graph_runtime"] = "fallback"
    return state
