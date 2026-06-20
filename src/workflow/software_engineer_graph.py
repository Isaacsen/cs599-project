from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from src.agents.bug_fixer import FixPlan, fix_repository
from src.agents.code_reviewer import ReviewReport, review_repository
from src.agents.llm_test_generator import LLMTestGenerationReport, generate_llm_pytest_tests
from src.agents.unit_test_writer import UnitTestReport, generate_missing_unit_tests
from src.llm.client import StaticLLMClient
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
    use_llm_tests: bool
    test_file_path: str
    llm_test_file_path: str
    max_functions: int
    mock_llm_response: str
    graph_runtime: str
    status: str
    scan: RepositoryScanResult
    review: ReviewReport
    fix_plan: FixPlan
    unit_tests: UnitTestReport
    llm_tests: LLMTestGenerationReport
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
    use_llm_tests: bool = False,
    test_file_path: str | Path = "tests/test_testguard_generated.py",
    llm_test_file_path: str | Path = "tests/test_testguard_llm_generated.py",
    max_functions: int = 8,
    mock_llm_response: str | None = None,
) -> SoftwareEngineerGraphResult:
    initial_state: SoftwareEngineerGraphState = {
        "project_path": str(Path(project_path).resolve()),
        "apply_fixes": apply_fixes,
        "apply_tests": apply_tests,
        "use_llm_tests": use_llm_tests,
        "test_file_path": str(test_file_path),
        "llm_test_file_path": str(llm_test_file_path),
        "max_functions": max_functions,
        "mock_llm_response": mock_llm_response or "",
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
    graph.add_node("fix", fix_node)
    graph.add_node("unit_tests", unit_tests_node)
    graph.add_node("llm_tests", llm_tests_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "scan")
    graph.add_edge("scan", "review")
    graph.add_edge("review", "fix")
    graph.add_edge("fix", "unit_tests")
    graph.add_conditional_edges(
        "unit_tests",
        _route_after_unit_tests,
        {
            "llm_tests": "llm_tests",
            "finish": "finish",
        },
    )
    graph.add_edge("llm_tests", "finish")
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


def unit_tests_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    scan = scan_repository(state["project_path"]) if state.get("apply_fixes", False) else state["scan"]
    unit_tests = generate_missing_unit_tests(
        state["project_path"],
        scan,
        apply_changes=state.get("apply_tests", False),
        test_file_path=state.get("test_file_path", "tests/test_testguard_generated.py"),
        max_functions=state.get("max_functions", 8),
    )
    return {
        "unit_tests": unit_tests,
        "node_trace": [*state.get("node_trace", []), "unit_tests"],
    }


def llm_tests_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    client = StaticLLMClient(state["mock_llm_response"]) if state.get("mock_llm_response") else None
    llm_tests = generate_llm_pytest_tests(
        state["project_path"],
        state["scan"],
        apply_changes=state.get("apply_tests", False),
        test_file_path=state.get("llm_test_file_path", "tests/test_testguard_llm_generated.py"),
        max_functions=state.get("max_functions", 8),
        client=client,
    )
    return {
        "llm_tests": llm_tests,
        "node_trace": [*state.get("node_trace", []), "llm_tests"],
    }


def finish_node(state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    return {
        "status": "completed",
        "node_trace": [*state.get("node_trace", []), "finish"],
    }


def format_software_engineer_graph_result(result: SoftwareEngineerGraphResult) -> str:
    state = result.state
    lines = [
        "[TestGuard Software Engineer LangGraph]",
        "",
        f"Project: {result.project_path}",
        f"Status: {state.get('status', 'unknown')}",
        f"Runtime: {result.graph_runtime}",
        f"Node Trace: {' -> '.join(result.node_trace)}",
        "",
        f"Review Findings: {result.finding_count}",
        f"Fix Edits: {result.fix_edit_count}",
        f"Generated Unit Tests: {result.generated_unit_test_count}",
        f"Generated LLM Tests: {result.generated_llm_test_count}",
    ]
    return "\n".join(lines)


def _route_after_unit_tests(state: SoftwareEngineerGraphState) -> str:
    if state.get("use_llm_tests", False):
        return "llm_tests"
    return "finish"


def _run_fallback_graph(initial_state: SoftwareEngineerGraphState) -> SoftwareEngineerGraphState:
    state: SoftwareEngineerGraphState = dict(initial_state)
    for node in [scan_node, review_node, fix_node, unit_tests_node]:
        state.update(node(state))
    if _route_after_unit_tests(state) == "llm_tests":
        state.update(llm_tests_node(state))
    state.update(finish_node(state))
    state["graph_runtime"] = "fallback"
    return state
