from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.tools.fix_writer import fix_plan_to_dict
from src.tools.llm_test_writer import llm_test_report_to_dict
from src.tools.review_writer import review_report_to_dict
from src.tools.unit_test_writer import unit_test_report_to_dict
from src.workflow.software_engineer_graph import SoftwareEngineerGraphResult


def software_engineer_graph_result_to_dict(result: SoftwareEngineerGraphResult) -> dict[str, Any]:
    state = result.state
    payload: dict[str, Any] = {
        "project_path": result.project_path,
        "status": state.get("status", "unknown"),
        "graph_runtime": result.graph_runtime,
        "node_trace": result.node_trace,
        "summary": {
            "finding_count": result.finding_count,
            "fix_edit_count": result.fix_edit_count,
            "generated_unit_test_count": result.generated_unit_test_count,
            "generated_llm_test_count": result.generated_llm_test_count,
            "apply_fixes": state.get("apply_fixes", False),
            "apply_tests": state.get("apply_tests", False),
            "use_llm_review": state.get("use_llm_review", False),
            "use_llm_tests": state.get("use_llm_tests", False),
            "run_sandbox": state.get("run_sandbox", False),
            "sandbox_executor": state.get("sandbox_executor", "docker"),
        },
    }
    if "scan" in state:
        payload["scan"] = asdict(state["scan"])
    if "review" in state:
        payload["review"] = review_report_to_dict(state["review"])
    if "llm_review" in state:
        payload["llm_review"] = _llm_review_to_dict(state["llm_review"])
    if "fix_plan" in state:
        payload["fix_plan"] = fix_plan_to_dict(state["fix_plan"])
    if "patch_review" in state:
        payload["patch_review"] = asdict(state["patch_review"])
    if "unit_tests" in state:
        payload["unit_tests"] = unit_test_report_to_dict(state["unit_tests"])
    if "llm_tests" in state:
        payload["llm_tests"] = llm_test_report_to_dict(state["llm_tests"])
    if "sandbox_validation" in state:
        payload["sandbox_validation"] = asdict(state["sandbox_validation"])
    if "repair_loop" in state:
        payload["repair_loop"] = asdict(state["repair_loop"])
    if "coverage_feedback" in state:
        payload["coverage_feedback"] = asdict(state["coverage_feedback"])
    return payload


def write_software_engineer_graph_result(result: SoftwareEngineerGraphResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(software_engineer_graph_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _llm_review_to_dict(report: Any) -> dict[str, Any]:
    return {
        "project_path": report.project_path,
        "status": report.status,
        "provider": report.provider,
        "model": report.model,
        "api_key_set": report.api_key_set,
        "api_key_env": report.api_key_env,
        "summary": {
            "finding_count": report.finding_count,
        },
        "findings": [asdict(finding) for finding in report.findings],
    }
