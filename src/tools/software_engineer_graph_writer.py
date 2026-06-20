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


def write_software_engineer_markdown(result: SoftwareEngineerGraphResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_software_engineer_markdown(result), encoding="utf-8")
    return path


def format_software_engineer_markdown(result: SoftwareEngineerGraphResult) -> str:
    state = result.state
    lines = [
        "# TestGuard Software Engineer Agent Report",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Project | `{result.project_path}` |",
        f"| Status | `{state.get('status', 'unknown')}` |",
        f"| Runtime | `{result.graph_runtime}` |",
        f"| Review Findings | {result.finding_count} |",
        f"| LLM Review Findings | {_count(state.get('llm_review'), 'finding_count')} |",
        f"| Fix Edits | {result.fix_edit_count} |",
        f"| Patch Review | `{_status(state.get('patch_review'))}` |",
        f"| Generated Unit Tests | {result.generated_unit_test_count} |",
        f"| Generated LLM Tests | {result.generated_llm_test_count} |",
        f"| Sandbox Validation | `{_status(state.get('sandbox_validation'))}` |",
        f"| Coverage | {_coverage_value(state.get('coverage_feedback'))} |",
        "",
        "## Agent Timeline",
        "",
        "| Step | Agent | Result |",
        "| --- | --- | --- |",
    ]
    for index, node in enumerate(result.node_trace, start=1):
        lines.append(f"| {index} | `{node}` | {_node_result(state, node)} |")

    lines.extend(["", "## Rule Review Findings", ""])
    lines.extend(_finding_table(state.get("review")))
    lines.extend(["", "## LLM Review Findings", ""])
    lines.extend(_finding_table(state.get("llm_review")))
    lines.extend(["", "## Fix Plan", ""])
    lines.extend(_fix_table(state.get("fix_plan")))
    lines.extend(["", "## Patch Review", ""])
    lines.extend(_patch_review_section(state.get("patch_review")))
    lines.extend(["", "## Sandbox Validation", ""])
    lines.extend(_sandbox_section(state.get("sandbox_validation")))
    lines.extend(["", "## Coverage Feedback", ""])
    lines.extend(_coverage_section(state.get("coverage_feedback")))
    lines.extend(["", "## Repair Loop", ""])
    lines.extend(_repair_section(state.get("repair_loop")))
    return "\n".join(lines).rstrip() + "\n"


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


def _status(report: Any) -> str:
    if report is None:
        return "not_run"
    return str(getattr(report, "status", "unknown"))


def _count(report: Any, attribute: str) -> int:
    if report is None:
        return 0
    return int(getattr(report, attribute, 0))


def _coverage_value(report: Any) -> str:
    if report is None:
        return "not_run"
    return f"{report.coverage_ratio:.0%}"


def _node_result(state: dict[str, Any], node: str) -> str:
    mapping = {
        "scan": ("scan", lambda: f"{len(state['scan'].source_files)} source file(s)"),
        "review": ("review", lambda: f"{state['review'].finding_count} finding(s)"),
        "llm_review": ("llm_review", lambda: f"{state['llm_review'].finding_count} finding(s)"),
        "fix": ("fix_plan", lambda: f"{state['fix_plan'].edit_count} edit(s)"),
        "patch_review": ("patch_review", lambda: state["patch_review"].status),
        "unit_tests": ("unit_tests", lambda: f"{state['unit_tests'].generated_test_count} test(s)"),
        "llm_tests": ("llm_tests", lambda: f"{state['llm_tests'].generated_test_count} test(s)"),
        "sandbox_validate": ("sandbox_validation", lambda: state["sandbox_validation"].status),
        "repair_loop": ("repair_loop", lambda: state["repair_loop"].status),
        "coverage_feedback": ("coverage_feedback", lambda: f"{state['coverage_feedback'].coverage_ratio:.0%}"),
        "finish": ("status", lambda: state.get("status", "unknown")),
    }
    if node not in mapping:
        return ""
    required_key, renderer = mapping[node]
    if required_key not in state:
        return ""
    return str(renderer())


def _finding_table(report: Any) -> list[str]:
    if report is None or not report.findings:
        return ["No findings."]
    lines = ["| Severity | Rule | Location | Message | Suggestion |", "| --- | --- | --- | --- | --- |"]
    for finding in report.findings[:8]:
        location = f"{finding.file_path}:{finding.line}" if finding.file_path else "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(finding.severity),
                    _cell(finding.rule),
                    _cell(location),
                    _cell(finding.message),
                    _cell(finding.suggestion),
                ]
            )
            + " |"
        )
    return lines


def _fix_table(report: Any) -> list[str]:
    if report is None or not report.edits:
        return ["No fix edits planned."]
    lines = ["| Rule | Location | Before | After |", "| --- | --- | --- | --- |"]
    for edit in report.edits[:8]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(edit.rule),
                    _cell(f"{edit.file_path}:{edit.line}"),
                    _cell(edit.before),
                    _cell(edit.after),
                ]
            )
            + " |"
        )
    return lines


def _patch_review_section(report: Any) -> list[str]:
    if report is None:
        return ["Patch review was not run."]
    if not report.findings:
        return [f"Status: `{report.status}`. No unsafe patch findings."]
    return _finding_table(report)


def _sandbox_section(report: Any) -> list[str]:
    if report is None:
        return ["Sandbox validation was not run."]
    analysis = report.analysis
    lines = [
        f"Status: `{report.status}`",
        "",
        "| Executor | Total | Passed | Failed | Errors |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| `{report.executor}` | {analysis.total} | {analysis.passed} | {analysis.failed} | {analysis.errors} |",
    ]
    if report.diagnosis.suggestions:
        lines.extend(["", "Suggestions:"])
        lines.extend(f"- {item}" for item in report.diagnosis.suggestions)
    return lines


def _coverage_section(report: Any) -> list[str]:
    if report is None:
        return ["Coverage feedback was not run."]
    lines = [
        f"Coverage ratio: **{report.coverage_ratio:.0%}**",
        "",
        f"Covered functions: {', '.join(f'`{item}`' for item in report.covered_functions) or 'none'}",
        f"Missing functions: {', '.join(f'`{item}`' for item in report.missing_functions) or 'none'}",
    ]
    return lines


def _repair_section(report: Any) -> list[str]:
    if report is None:
        return ["Repair loop was not run."]
    lines = [
        f"Status: `{report.status}`",
        f"Next step: `{report.next_step}`",
        "",
        "Actions:",
    ]
    lines.extend(f"- {item}" for item in report.actions)
    return lines


def _cell(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return text.replace("|", "\\|")
