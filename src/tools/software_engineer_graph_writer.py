from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.llm_code_fixer import LLMCodeFixReport, replacement_digest
from src.agents.llm_fix_planner import LLMFixPlan
from src.tools.llm_test_writer import llm_test_report_to_dict
from src.workflow.software_engineer_graph import SoftwareEngineerGraphResult


def software_engineer_graph_result_to_dict(result: SoftwareEngineerGraphResult) -> dict[str, Any]:
    state = result.state
    payload: dict[str, Any] = {
        "project_path": result.project_path,
        "status": state.get("status", "unknown"),
        "graph_runtime": result.graph_runtime,
        "node_trace": result.node_trace,
        "summary": {
            "llm_fix_count": _fix_count(state),
            "generated_llm_test_count": result.generated_llm_test_count,
            "apply_fixes": state.get("apply_fixes", False),
            "apply_tests": state.get("apply_tests", False),
            "run_sandbox": state.get("run_sandbox", False),
            "sandbox_executor": state.get("sandbox_executor", "docker"),
            "attempted_finding_indexes": state.get(
                "attempted_finding_indexes",
                state.get("processed_finding_indexes", []),
            ),
            "resolved_finding_indexes": state.get("resolved_finding_indexes", []),
            "unresolved_finding_indexes": _unresolved_finding_indexes(state),
            "processed_finding_indexes": state.get("processed_finding_indexes", []),
            "finding_rounds": state.get("finding_round", 0),
        },
    }
    if "scan" in state:
        payload["scan"] = asdict(state["scan"])
    if "llm_review" in state:
        payload["llm_review"] = _llm_review_to_dict(state["llm_review"])
    if "llm_fix_plan" in state:
        payload["llm_fix_plan"] = _llm_fix_plan_to_dict(state["llm_fix_plan"])
    if "llm_fix_plan_history" in state:
        payload["llm_fix_plan_history"] = [_llm_fix_plan_to_dict(plan) for plan in state["llm_fix_plan_history"]]
    if "llm_fix" in state:
        payload["llm_fix"] = _llm_fix_to_dict(state["llm_fix"])
    if "llm_fix_history" in state:
        payload["llm_fix_history"] = [_llm_fix_to_dict(report) for report in state["llm_fix_history"]]
    if "llm_tests" in state:
        payload["llm_tests"] = llm_test_report_to_dict(state["llm_tests"])
    if "llm_tests_history" in state:
        payload["llm_tests_history"] = [llm_test_report_to_dict(report) for report in state["llm_tests_history"]]
    if "sandbox_validation" in state:
        payload["sandbox_validation"] = asdict(state["sandbox_validation"])
    if "sandbox_validation_history" in state:
        payload["sandbox_validation_history"] = [asdict(report) for report in state["sandbox_validation_history"]]
    if "repair_loop" in state:
        payload["repair_loop"] = asdict(state["repair_loop"])
    if "repair_history" in state:
        payload["repair_history"] = [asdict(report) for report in state["repair_history"]]
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
        "# Software Engineer Agent Report",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Project | `{result.project_path}` |",
        f"| Status | `{state.get('status', 'unknown')}` |",
        f"| Runtime | `{result.graph_runtime}` |",
        f"| Repo Scan | `{_status(state.get('scan'))}` |",
        f"| LLM Review Findings | {_count(state.get('llm_review'), 'finding_count')} |",
        f"| Attempted Findings | {len(state.get('attempted_finding_indexes', state.get('processed_finding_indexes', [])))} |",
        f"| Resolved Findings | {len(state.get('resolved_finding_indexes', []))} |",
        f"| Unresolved Findings | {len(_unresolved_finding_indexes(state))} |",
        f"| Finding Rounds | {state.get('finding_round', 0)} |",
        f"| LLM Fixes | {_fix_count(state)} |",
        f"| Generated LLM Tests | {result.generated_llm_test_count} |",
        f"| Sandbox Validation | `{_status(state.get('sandbox_validation'))}` |",
        f"| Coverage | {_coverage_value(state.get('coverage_feedback'))} |",
        "",
        "## Agent Timeline",
        "",
        "| Step | Agent | Result |",
        "| --- | --- | --- |",
    ]
    occurrences: dict[str, int] = {}
    for index, node in enumerate(result.node_trace, start=1):
        occurrences[node] = occurrences.get(node, 0) + 1
        lines.append(f"| {index} | `{node}` | {_node_result(state, node, occurrences[node])} |")

    lines.extend(["", "## Repo Scan", ""])
    lines.extend(_scan_section(state.get("scan")))
    lines.extend(["", "## LLM Review Findings", ""])
    unresolved = _unresolved_finding_indexes(state)
    if unresolved:
        lines.extend(
            [
                f"Review resolution: **{len(unresolved)} unresolved finding(s)**. "
                "Passing sandbox tests and 100% generated-test coverage do not mean review findings are fixed "
                "unless fixes were applied and validated.",
                "",
            ]
        )
    lines.extend(_finding_table(state.get("llm_review")))
    lines.extend(["", "## LLM Fix Plan", ""])
    lines.extend(_fix_plan_section(state.get("llm_fix_plan")))
    if state.get("llm_fix_plan_history"):
        lines.extend(["", "## LLM Fix Plan History", ""])
        lines.extend(_fix_plan_history_section(state.get("llm_fix_plan_history")))
    lines.extend(["", "## LLM Code Fixes", ""])
    lines.extend(_fix_section(state.get("llm_fix")))
    if state.get("llm_fix_history"):
        lines.extend(["", "## LLM Code Fix History", ""])
        lines.extend(_fix_history_section(state.get("llm_fix_history")))
    lines.extend(["", "## Sandbox Validation", ""])
    lines.extend(_sandbox_section(state.get("sandbox_validation")))
    lines.extend(["", "## Coverage Feedback", ""])
    lines.extend(_coverage_section(state.get("coverage_feedback")))
    lines.extend(["", "## Repair Loop", ""])
    lines.extend(_repair_section(state.get("repair_loop")))
    if state.get("repair_history"):
        lines.extend(["", "## Repair History", ""])
        lines.extend(_repair_history_section(state.get("repair_history")))
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


def _llm_fix_to_dict(report: LLMCodeFixReport) -> dict[str, Any]:
    return {
        "project_path": report.project_path,
        "status": report.status,
        "applied": report.applied,
        "provider": report.provider,
        "model": report.model,
        "api_key_set": report.api_key_set,
        "api_key_env": report.api_key_env,
        "summary": {
            "fix_count": report.fix_count,
        },
        "error_summary": _fix_error_summary(report),
        "patch_review": asdict(report.patch_review) if report.patch_review else None,
        "fixes": [
            {
                "file_path": fix.file_path,
                "summary": fix.summary,
                "applied": fix.applied,
                "replacement_sha256": replacement_digest(fix.replacement_content),
                "replacement_char_count": len(fix.replacement_content),
            }
            for fix in report.fixes
        ],
    }


def _llm_fix_plan_to_dict(plan: LLMFixPlan) -> dict[str, Any]:
    return {
        "status": plan.status,
        "rationale": plan.rationale,
        "summary": {
            "target_count": plan.target_count,
            "remaining_count": plan.remaining_count,
        },
        "planner": plan.planner,
        "fallback_reason": plan.fallback_reason,
        "raw_response_excerpt": _excerpt(plan.raw_response),
        "targets": [
            {
                "finding_index": target.finding_index,
                "file_path": target.file_path,
                "line": target.line,
                "severity": target.severity,
                "rule": target.rule,
                "reason": target.reason,
            }
            for target in plan.targets
        ],
    }


def _status(report: Any) -> str:
    if report is None:
        return "not_run"
    return str(getattr(report, "status", "unknown"))


def _count(report: Any, attribute: str) -> int:
    if report is None:
        return 0
    return int(getattr(report, attribute, 0))


def _fix_count(state: dict[str, Any]) -> int:
    history = state.get("llm_fix_history") or []
    if history:
        return sum(int(getattr(report, "fix_count", 0)) for report in history)
    return _count(state.get("llm_fix"), "fix_count")


def _coverage_value(report: Any) -> str:
    if report is None:
        return "not_run"
    return f"{report.coverage_ratio:.0%}"


def _node_result(state: dict[str, Any], node: str, occurrence: int = 1) -> str:
    mapping = {
        "scan": ("scan", lambda: f"{state['scan'].status}, {len(state['scan'].source_files)} source file(s)"),
        "llm_review": ("llm_review", lambda: f"{state['llm_review'].finding_count} finding(s)"),
        "llm_fix_plan": (
            "llm_fix_plan",
            lambda: _history_result(
                state,
                "llm_fix_plan_history",
                "llm_fix_plan",
                occurrence,
                lambda plan: f"round {occurrence}, {plan.target_count} target(s), {plan.status}, remaining={plan.remaining_count}",
            ),
        ),
        "llm_fix": ("llm_fix", lambda: _history_result(state, "llm_fix_history", "llm_fix", occurrence, _fix_result)),
        "llm_tests": (
            "llm_tests",
            lambda: _history_result(state, "llm_tests_history", "llm_tests", occurrence, _llm_test_result),
        ),
        "sandbox_validate": (
            "sandbox_validation",
            lambda: _history_result(
                state,
                "sandbox_validation_history",
                "sandbox_validation",
                occurrence,
                lambda report: report.status,
            ),
        ),
        "repair_loop": (
            "repair_loop",
            lambda: _history_result(
                state,
                "repair_history",
                "repair_loop",
                occurrence,
                lambda report: report.status,
            ),
        ),
        "coverage_feedback": ("coverage_feedback", lambda: f"{state['coverage_feedback'].coverage_ratio:.0%}"),
        "finish": ("status", lambda: state.get("status", "unknown")),
    }
    if node not in mapping:
        return ""
    required_key, renderer = mapping[node]
    if required_key not in state:
        return ""
    return str(renderer())


def _history_result(
    state: dict[str, Any],
    history_key: str,
    fallback_key: str,
    occurrence: int,
    renderer: Any,
) -> str:
    history = state.get(history_key) or []
    index = occurrence - 1
    if 0 <= index < len(history):
        return str(renderer(history[index]))
    return str(renderer(state[fallback_key]))


def _fix_result(report: Any) -> str:
    return f"{report.fix_count} fix(es), {report.status}"


def _llm_test_result(report: Any) -> str:
    return f"{report.generated_test_count} test(s), {report.status}"


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


def _scan_section(report: Any) -> list[str]:
    if report is None:
        return ["Repository scan was not run."]
    lines = [
        f"Status: `{report.status}`",
        "",
        "| Item | Count |",
        "| --- | ---: |",
        f"| Source files | {len(report.source_files)} |",
        f"| Test files | {len(report.test_files)} |",
        f"| Config files | {len(report.config_files or [])} |",
        f"| Dependency files | {len(report.dependency_files or [])} |",
        f"| Package roots | {len(report.package_roots or [])} |",
        f"| Entry points | {len(report.entry_points or [])} |",
    ]
    if report.error_summary:
        lines.extend(["", f"Failure summary: `{_cell(report.error_summary)}`"])
    if report.issues:
        lines.extend(["", "Scan issues:"])
        lines.extend(f"- [{issue.severity}] {_cell(issue.message)}" for issue in report.issues[:6])
    return lines


def _fix_section(report: Any) -> list[str]:
    if report is None:
        return ["LLM code fixer was not run."]
    if not report.fixes:
        lines = [f"Status: `{report.status}`. No fixes were proposed."]
        error_summary = _fix_error_summary(report)
        if error_summary:
            lines.extend(["", f"Failure summary: `{_cell(error_summary)}`"])
        return lines
    lines = []
    if report.patch_review:
        lines.extend(
            [
                f"Patch review: `{'passed' if report.patch_review.passed else 'failed'}` "
                f"({report.patch_review.violation_count} violation(s))",
                "",
            ]
        )
        if report.patch_review.violations:
            lines.extend(f"- {_cell(item)}" for item in report.patch_review.violations[:5])
            lines.append("")
    lines.extend(["| File | Applied | Summary | Replacement SHA-256 |", "| --- | --- | --- | --- |"])
    for fix in report.fixes[:8]:
        lines.append(
            f"| `{_cell(fix.file_path)}` | `{fix.applied}` | {_cell(fix.summary)} | "
            f"`{replacement_digest(fix.replacement_content)[:12]}` |"
        )
    return lines


def _fix_plan_section(plan: Any) -> list[str]:
    if plan is None:
        return ["LLM fix planner was not run."]
    if not plan.targets:
        lines = [f"Status: `{plan.status}`. No fix targets were selected. Remaining findings: {plan.remaining_count}."]
        if plan.fallback_reason:
            lines.append(f"Fallback reason: `{_cell(plan.fallback_reason)}`")
        return lines
    lines = [
        f"Planner: `{plan.planner}`",
        f"Remaining findings after this plan: **{plan.remaining_count}**",
        "",
    ]
    if plan.fallback_reason:
        lines.extend([f"Fallback reason: `{_cell(plan.fallback_reason)}`", ""])
    lines.extend(["| Order | Finding | Severity | Reason |", "| ---: | --- | --- | --- |"])
    for order, target in enumerate(plan.targets, start=1):
        finding = f"{target.file_path}:{target.line} ({target.rule})"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(order),
                    _cell(finding),
                    _cell(target.severity),
                    _cell(target.reason),
                ]
            )
            + " |"
        )
    return lines


def _fix_plan_history_section(history: Any) -> list[str]:
    if not history:
        return ["No fix-plan history was recorded."]
    lines = [
        "| Round | Planner | Targets | Remaining | Fallback | Rationale |",
        "| ---: | --- | --- | ---: | --- | --- |",
    ]
    for round_index, plan in enumerate(history, start=1):
        targets = ", ".join(f"#{target.finding_index} {target.file_path}:{target.line}" for target in plan.targets)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(round_index),
                    _cell(plan.planner),
                    _cell(targets or "none"),
                    str(plan.remaining_count),
                    _cell(plan.fallback_reason),
                    _cell(plan.rationale),
                ]
            )
            + " |"
        )
    return lines


def _fix_history_section(history: Any) -> list[str]:
    if not history:
        return ["No code-fix history was recorded."]
    lines = [
        "| Round | Status | Fixes | Applied | Patch Review | Summary | Error |",
        "| ---: | --- | ---: | --- | --- | --- | --- |",
    ]
    for round_index, report in enumerate(history, start=1):
        summaries = "; ".join(fix.summary for fix in report.fixes[:3])
        lines.append(
            "| "
            + " | ".join(
                [
                    str(round_index),
                    _cell(report.status),
                    str(report.fix_count),
                    str(report.applied),
                    _patch_review_status(report),
                    _cell(summaries or "none"),
                    _cell(_fix_error_summary(report)),
                ]
            )
            + " |"
        )
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


def _repair_history_section(history: Any) -> list[str]:
    if not history:
        return ["No repair iterations were recorded."]
    lines = ["| Iteration | Status | Next Step | First Action |", "| ---: | --- | --- | --- |"]
    for report in history:
        first_action = report.actions[0] if report.actions else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    str(report.iteration),
                    _cell(report.status),
                    _cell(report.next_step),
                    _cell(first_action),
                ]
            )
            + " |"
        )
    return lines


def _cell(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return text.replace("|", "\\|")


def _excerpt(value: str, limit: int = 500) -> str:
    text = value.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _fix_error_summary(report: Any) -> str:
    if report is None or report.fix_count:
        return ""
    raw_response = getattr(report, "raw_response", "")
    if not raw_response:
        return ""
    return _excerpt(raw_response, 240)


def _patch_review_status(report: Any) -> str:
    patch_review = getattr(report, "patch_review", None)
    if patch_review is None:
        return "not_run"
    return "passed" if patch_review.passed else f"failed ({patch_review.violation_count})"


def _unresolved_finding_indexes(state: dict[str, Any]) -> list[int]:
    review = state.get("llm_review")
    if review is None:
        return []
    resolved = set(state.get("resolved_finding_indexes", []))
    return [index for index, _finding in enumerate(review.findings) if index not in resolved]
