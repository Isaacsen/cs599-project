from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from src.agents.bug_fixer import FixPlan, fix_repository
from src.agents.code_reviewer import ReviewReport, review_repository
from src.agents.coverage_feedback import CoverageFeedbackReport, build_coverage_feedback
from src.agents.llm_code_reviewer import LLMCodeReviewReport, review_repository_with_llm
from src.agents.llm_test_generator import LLMTestGenerationReport, generate_llm_pytest_tests
from src.agents.patch_reviewer import PatchReviewReport, review_fix_plan
from src.agents.repair_loop import RepairLoopReport, plan_repair_iteration
from src.agents.sandbox_validator import SandboxValidationReport, validate_generated_tests_in_sandbox
from src.agents.unit_test_writer import UnitTestReport, generate_missing_unit_tests
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
    use_llm_review: bool
    use_llm_tests: bool
    run_sandbox: bool
    sandbox_executor: str
    docker_image: str
    timeout_seconds: int
    repair_iterations: int
    test_file_path: str
    llm_test_file_path: str
    max_functions: int
    graph_runtime: str
    status: str
    scan: RepositoryScanResult
    review: ReviewReport
    llm_review: LLMCodeReviewReport
    fix_plan: FixPlan
    patch_review: PatchReviewReport
    unit_tests: UnitTestReport
    llm_tests: LLMTestGenerationReport
    sandbox_validation: SandboxValidationReport
    repair_loop: RepairLoopReport
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
    def finding_count(self) -> int:
        review = self.state.get("review")
        return review.finding_count if review else 0

    @property
    def fix_edit_count(self) -> int:
        fix_plan = self.state.get("fix_plan")
        return fix_plan.edit_count if fix_plan else 0

    @property
    def generated_unit_test_count(self) -> int:
        unit_tests = self.state.get("unit_tests")
        return unit_tests.generated_test_count if unit_tests else 0

    @property
    def generated_llm_test_count(self) -> int:
        llm_tests = self.state.get("llm_tests")
        return llm_tests.generated_test_count if llm_tests else 0


def run_software_engineer_graph(
    project_path: str | Path,
    apply_fixes: bool = False,
    apply_tests: bool = False,
    use_llm_review: bool = False,
    use_llm_tests: bool = False,
    run_sandbox: bool = False,
    sandbox_executor: str = "docker",
    docker_image: str = "software-engineer-agent-python:latest",
    timeout_seconds: int = 30,
    repair_iterations: int = 1,
    test_file_path: str | Path = "tests/test_software_engineer_generated.py",
    llm_test_file_path: str | Path = "tests/test_software_engineer_llm_generated.py",
    max_functions: int = 8,
) -> SoftwareEngineerGraphResult:
    initial_state: SoftwareEngineerGraphState = {
        "project_path": str(Path(project_path).resolve()),
        "apply_fixes": apply_fixes,
        "apply_tests": apply_tests,
        "use_llm_review": use_llm_review,
        "use_llm_tests": use_llm_tests,
        "run_sandbox": run_sandbox,
        "sandbox_executor": sandbox_executor,
        "docker_image": docker_image,
        "timeout_seconds": timeout_seconds,
        "repair_iterations": repair_iterations,
        "test_file_path": str(test_file_path),
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
    graph.add_node("review", review_node)
    graph.add_node("llm_review", llm_review_node)
    graph.add_node("fix", fix_node)
    graph.add_node("patch_review", patch_review_node)
    graph.add_node("unit_tests", unit_tests_node)
    graph.add_node("llm_tests", llm_tests_node)
    graph.add_node("sandbox_validate", sandbox_validate_node)
    graph.add_node("repair_loop", repair_loop_node)
    graph.add_node("coverage_feedback", coverage_feedback_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "scan")
    graph.add_edge("scan", "review")
    graph.add_conditional_edges(
        "review",
        _route_after_review,
        {
            "llm_review": "llm_review",
            "fix": "fix",
        },
    )
    graph.add_edge("llm_review", "fix")
    graph.add_edge("fix", "patch_review")
    graph.add_edge("patch_review", "unit_tests")
    graph.add_conditional_edges(
        "unit_tests",
        _route_after_unit_tests,
        {
            "llm_tests": "llm_tests",
            "sandbox_validate": "sandbox_validate",
            "coverage_feedback": "coverage_feedback",
        },
    )
    graph.add_conditional_edges(
        "llm_tests",
        _route_after_generated_tests,
        {
            "sandbox_validate": "sandbox_validate",
            "coverage_feedback": "coverage_feedback",
        },
    )
    graph.add_edge("sandbox_validate", "repair_loop")
    graph.add_edge("repair_loop", "coverage_feedback")
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


def review_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    review = review_repository(state["project_path"], state["scan"])
    return {
        "review": review,
        "node_trace": [*state.get("node_trace", []), "review"],
    }


def llm_review_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    llm_review = review_repository_with_llm(state["project_path"], state["scan"])
    return {
        "llm_review": llm_review,
        "node_trace": [*state.get("node_trace", []), "llm_review"],
    }


def fix_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    fix_plan = fix_repository(
        state["project_path"],
        state["scan"],
        apply_changes=state.get("apply_fixes", False),
    )
    return {
        "fix_plan": fix_plan,
        "node_trace": [*state.get("node_trace", []), "fix"],
    }


def patch_review_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    patch_review = review_fix_plan(state["project_path"], state["scan"], state["fix_plan"])
    return {
        "patch_review": patch_review,
        "node_trace": [*state.get("node_trace", []), "patch_review"],
    }


def unit_tests_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    scan = scan_repository(state["project_path"]) if state.get("apply_fixes", False) else state["scan"]
    unit_tests = generate_missing_unit_tests(
        state["project_path"],
        scan,
        apply_changes=state.get("apply_tests", False),
        test_file_path=state.get("test_file_path", "tests/test_software_engineer_generated.py"),
        max_functions=state.get("max_functions", 8),
    )
    return {
        "unit_tests": unit_tests,
        "node_trace": [*state.get("node_trace", []), "unit_tests"],
    }


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
        "node_trace": [*state.get("node_trace", []), "llm_tests"],
    }


def sandbox_validate_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    sandbox_validation = validate_generated_tests_in_sandbox(
        state["project_path"],
        unit_tests=state.get("unit_tests"),
        llm_tests=state.get("llm_tests"),
        executor=state.get("sandbox_executor", "docker"),
        docker_image=state.get("docker_image", "software-engineer-agent-python:latest"),
        timeout_seconds=state.get("timeout_seconds", 30),
    )
    return {
        "sandbox_validation": sandbox_validation,
        "node_trace": [*state.get("node_trace", []), "sandbox_validate"],
    }


def repair_loop_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    repair_loop = plan_repair_iteration(
        state.get("patch_review"),
        state.get("sandbox_validation"),
        max_iterations=state.get("repair_iterations", 1),
    )
    return {
        "repair_loop": repair_loop,
        "node_trace": [*state.get("node_trace", []), "repair_loop"],
    }


def coverage_feedback_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    coverage_feedback = build_coverage_feedback(
        state["project_path"],
        state["scan"],
        unit_tests=state.get("unit_tests"),
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
        f"  Rule Review Findings: {result.finding_count}",
        f"  LLM Review Findings: {_llm_review_count(state)}",
        f"  Fix Edits Planned: {result.fix_edit_count}",
        f"  Patch Review: {_patch_review_status(state)}",
        f"  Generated Unit Tests: {result.generated_unit_test_count}",
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
        "review": "Rule code review",
        "llm_review": "LLM code review",
        "fix": "Bug-fix planning",
        "patch_review": "Patch review",
        "unit_tests": "Unit test writer",
        "llm_tests": "LLM test writer",
        "sandbox_validate": "Sandbox pytest",
        "repair_loop": "Repair loop",
        "coverage_feedback": "Coverage feedback",
        "finish": "Finish",
    }
    return [
        f"  {index:02d}. {labels.get(node, node)} - {_node_status(state, node)}"
        for index, node in enumerate(node_trace, start=1)
    ]


def _node_status(state: SoftwareEngineerGraphState, node: str) -> str:
    if node == "scan" and "scan" in state:
        return f"{len(state['scan'].source_files)} source file(s)"
    if node == "review" and "review" in state:
        return f"{state['review'].finding_count} finding(s)"
    if node == "llm_review" and "llm_review" in state:
        return f"{state['llm_review'].finding_count} finding(s)"
    if node == "fix" and "fix_plan" in state:
        return f"{state['fix_plan'].edit_count} edit(s)"
    if node == "patch_review" and "patch_review" in state:
        return state["patch_review"].status
    if node == "unit_tests" and "unit_tests" in state:
        return f"{state['unit_tests'].generated_test_count} test(s)"
    if node == "llm_tests" and "llm_tests" in state:
        return f"{state['llm_tests'].generated_test_count} test(s)"
    if node == "sandbox_validate" and "sandbox_validation" in state:
        report = state["sandbox_validation"]
        return f"{report.status}, {report.analysis.passed}/{report.analysis.total} passed"
    if node == "repair_loop" and "repair_loop" in state:
        return f"{state['repair_loop'].status}, next={state['repair_loop'].next_step}"
    if node == "coverage_feedback" and "coverage_feedback" in state:
        return f"{state['coverage_feedback'].coverage_ratio:.0%}"
    if node == "finish":
        return state.get("status", "unknown")
    return "not_run"


def _format_highlights(state: SoftwareEngineerGraphState) -> list[str]:
    highlights: list[str] = []
    review = state.get("review")
    if review and review.findings:
        first = review.findings[0]
        highlights.append(f"  - Rule review: [{first.severity}] {first.rule} at {first.file_path}:{first.line}")
    llm_review = state.get("llm_review")
    if llm_review and llm_review.findings:
        first = llm_review.findings[0]
        highlights.append(f"  - LLM review: [{first.severity}] {first.message}")
    patch_review = state.get("patch_review")
    if patch_review:
        highlights.append(f"  - Patch review: {patch_review.status}")
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


def _patch_review_status(state: SoftwareEngineerGraphState) -> str:
    report = state.get("patch_review")
    if report is None:
        return "not_run"
    return report.status


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


def _route_after_unit_tests(state: SoftwareEngineerGraphState) -> str:
    if state.get("use_llm_tests", False):
        return "llm_tests"
    return _route_after_generated_tests(state)


def _route_after_review(state: SoftwareEngineerGraphState) -> str:
    if state.get("use_llm_review", False):
        return "llm_review"
    return "fix"


def _route_after_generated_tests(state: SoftwareEngineerGraphState) -> str:
    if state.get("run_sandbox", False):
        return "sandbox_validate"
    return "coverage_feedback"


def _run_fallback_graph(initial_state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    state: SoftwareEngineerGraphState = dict(initial_state)
    for node in [scan_node, review_node]:
        state.update(node(state))
    if _route_after_review(state) == "llm_review":
        state.update(llm_review_node(state))
    for node in [fix_node, patch_review_node, unit_tests_node]:
        state.update(node(state))
    if _route_after_unit_tests(state) == "llm_tests":
        state.update(llm_tests_node(state))
    if _route_after_generated_tests(state) == "sandbox_validate":
        state.update(sandbox_validate_node(state))
        state.update(repair_loop_node(state))
    state.update(coverage_feedback_node(state))
    state.update(finish_node(state))
    state["graph_runtime"] = "fallback"
    return state
