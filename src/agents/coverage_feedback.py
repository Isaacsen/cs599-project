from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from src.agents.llm_test_generator import LLMTestGenerationReport
from src.agents.unit_test_writer import UnitTestReport
from src.tools.repo_scanner import RepositoryScanResult


@dataclass(frozen=True)
class CoverageFeedbackReport:
    project_path: str
    total_functions: int
    covered_functions: list[str]
    missing_functions: list[str]
    coverage_ratio: float
    suggestions: list[str]


def build_coverage_feedback(
    project_path: str | Path,
    scan: RepositoryScanResult,
    unit_tests: UnitTestReport | None = None,
    llm_tests: LLMTestGenerationReport | None = None,
) -> CoverageFeedbackReport:
    root = Path(project_path).resolve()
    public_functions = _public_functions(root, scan.source_files)
    covered = set()
    for report in (unit_tests, llm_tests):
        if report is not None and report.suite is not None:
            covered.update(report.suite.covered_functions)
    missing = sorted(function for function in public_functions if function not in covered)
    total = len(public_functions)
    ratio = 1.0 if total == 0 else (total - len(missing)) / total
    suggestions = [
        f"Add tests for {function}."
        for function in missing
    ] or ["Generated tests cover all discovered public functions."]
    return CoverageFeedbackReport(
        project_path=str(root),
        total_functions=total,
        covered_functions=sorted(covered),
        missing_functions=missing,
        coverage_ratio=ratio,
        suggestions=suggestions,
    )


def _public_functions(root: Path, source_files: list[str]) -> list[str]:
    functions: list[str] = []
    for relative_file in source_files:
        path = root / relative_file
        if not path.exists():
            continue
        module_name = Path(relative_file).with_suffix("").as_posix().replace("/", ".")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                functions.append(f"{module_name}.{node.name}")
    return sorted(functions)
