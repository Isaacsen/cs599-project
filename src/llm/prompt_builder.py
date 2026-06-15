from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.test_planner import TestPlan


MAX_SOURCE_CHARS = 8000


@dataclass(frozen=True)
class LLMTestPrompt:
    system: str
    user: str
    covered_functions: list[str]


def build_test_generation_prompt(
    project_path: str | Path,
    test_plan: TestPlan,
) -> LLMTestPrompt:
    root = Path(project_path).resolve()
    source_context = _collect_source_context(root, test_plan)
    plan_context = _format_plan(test_plan)

    system = (
        "You are TestGuard Agent, an expert Python test generation assistant. "
        "Generate safe pytest tests only. Do not use network access, subprocesses, "
        "file system mutation, eval, exec, or hardcoded secrets."
    )
    user = "\n\n".join(
        [
            "Generate pytest tests for the following planned cases.",
            "Return only Python code for one pytest file.",
            "Test plan:",
            plan_context,
            "Source context:",
            source_context,
        ]
    )

    return LLMTestPrompt(
        system=system,
        user=user,
        covered_functions=test_plan.covered_functions,
    )


def _format_plan(test_plan: TestPlan) -> str:
    if not test_plan.items:
        return "- No public functions discovered."

    lines: list[str] = []
    for index, item in enumerate(test_plan.items, start=1):
        lines.extend(
            [
                f"{index}. Function: {item.qualified_name}",
                f"   Scenario: {item.scenario}",
                f"   Rationale: {item.rationale}",
            ]
        )
    return "\n".join(lines)


def _collect_source_context(root: Path, test_plan: TestPlan) -> str:
    module_names = sorted({item.module_name for item in test_plan.items})
    chunks: list[str] = []

    for module_name in module_names:
        source_path = root / Path(*module_name.split(".")).with_suffix(".py")
        if not source_path.exists():
            continue
        content = source_path.read_text(encoding="utf-8")
        chunks.append(f"# {source_path.relative_to(root).as_posix()}\n{content}")

    combined = "\n\n".join(chunks)
    if len(combined) > MAX_SOURCE_CHARS:
        return combined[:MAX_SOURCE_CHARS] + "\n# ... truncated ..."
    return combined
