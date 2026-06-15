from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from src.tools.repo_scanner import RepositoryScanResult


@dataclass(frozen=True)
class FunctionSummary:
    module_name: str
    function_name: str
    arg_count: int

    @property
    def qualified_name(self) -> str:
        return f"{self.module_name}.{self.function_name}"


@dataclass(frozen=True)
class TestPlanItem:
    module_name: str
    function_name: str
    scenario: str
    rationale: str

    @property
    def qualified_name(self) -> str:
        return f"{self.module_name}.{self.function_name}"


@dataclass(frozen=True)
class TestPlan:
    items: list[TestPlanItem]

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def covered_functions(self) -> list[str]:
        return [item.qualified_name for item in self.items]


def plan_tests(
    project_path: str | Path,
    scan: RepositoryScanResult,
    max_functions: int = 8,
) -> TestPlan:
    root = Path(project_path).resolve()
    summaries = discover_public_functions(root, scan.source_files)[:max_functions]
    return TestPlan(items=[_plan_item(summary) for summary in summaries])


def discover_public_functions(root: Path, source_files: list[str]) -> list[FunctionSummary]:
    summaries: list[FunctionSummary] = []
    for relative_file in source_files:
        path = root / relative_file
        if path.name == "__init__.py":
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            tree = ast.parse(path.read_text())

        module_name = _module_name_from_path(relative_file)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_"):
                continue
            summaries.append(
                FunctionSummary(
                    module_name=module_name,
                    function_name=node.name,
                    arg_count=len(node.args.args),
                )
            )
    return summaries


def _plan_item(summary: FunctionSummary) -> TestPlanItem:
    lower_name = summary.function_name.lower()
    if lower_name in {"add", "sum_numbers", "sum_values"} or lower_name.startswith("add_"):
        return TestPlanItem(
            module_name=summary.module_name,
            function_name=summary.function_name,
            scenario="numeric addition happy path",
            rationale="Addition-like functions should preserve basic arithmetic behavior.",
        )
    if lower_name in {"subtract", "sub"} or lower_name.startswith("subtract_"):
        return TestPlanItem(
            module_name=summary.module_name,
            function_name=summary.function_name,
            scenario="numeric subtraction happy path",
            rationale="Subtraction-like functions should preserve basic arithmetic behavior.",
        )
    if lower_name in {"multiply", "mul"} or lower_name.startswith("multiply_"):
        return TestPlanItem(
            module_name=summary.module_name,
            function_name=summary.function_name,
            scenario="numeric multiplication happy path",
            rationale="Multiplication-like functions should preserve basic arithmetic behavior.",
        )
    if lower_name in {"divide", "div"} or lower_name.startswith("divide_"):
        return TestPlanItem(
            module_name=summary.module_name,
            function_name=summary.function_name,
            scenario="division happy path and zero-division boundary",
            rationale="Division-like functions need both normal input and denominator-zero coverage.",
        )
    if lower_name.startswith("is_") or lower_name.startswith("has_"):
        return TestPlanItem(
            module_name=summary.module_name,
            function_name=summary.function_name,
            scenario="predicate returns boolean",
            rationale="Predicate-like functions should return a boolean value.",
        )
    return TestPlanItem(
        module_name=summary.module_name,
        function_name=summary.function_name,
        scenario="public callable smoke test",
        rationale="Unknown public functions should at least remain importable and callable.",
    )


def _module_name_from_path(relative_file: str) -> str:
    path = Path(relative_file)
    return ".".join(path.with_suffix("").parts)
