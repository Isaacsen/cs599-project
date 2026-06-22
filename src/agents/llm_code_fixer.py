from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.code_reviewer import ReviewFinding
from src.agents.llm_fix_planner import LLMFixPlan, selected_findings
from src.agents.llm_code_reviewer import LLMCodeReviewReport
from src.agents.sandbox_validator import SandboxValidationReport
from src.llm.client import LLMClient, OpenAICompatibleLLMClient
from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt
from src.tools.repo_scanner import RepositoryScanResult


MAX_SOURCE_CHARS = 12000


@dataclass(frozen=True)
class LLMCodeFix:
    file_path: str
    summary: str
    replacement_content: str
    applied: bool


@dataclass(frozen=True)
class LLMCodeFixReport:
    project_path: str
    status: str
    applied: bool
    provider: str
    model: str
    api_key_set: bool
    api_key_env: str
    fixes: list[LLMCodeFix]
    raw_response: str = ""

    @property
    def fix_count(self) -> int:
        return len(self.fixes)


def fix_code_with_llm(
    project_path: str | Path,
    scan: RepositoryScanResult,
    llm_review: LLMCodeReviewReport | None = None,
    fix_plan: LLMFixPlan | None = None,
    sandbox_validation: SandboxValidationReport | None = None,
    repair_actions: list[str] | None = None,
    apply_changes: bool = False,
    client: LLMClient | None = None,
    config: LLMConfig | None = None,
    max_files: int = 6,
) -> LLMCodeFixReport:
    root = Path(project_path).resolve()
    active_config = config or LLMConfig.from_env()
    if client is None and not active_config.api_key_set and active_config.provider != "ollama":
        return LLMCodeFixReport(
            project_path=str(root),
            status="skipped_missing_api_key",
            applied=False,
            provider=active_config.provider,
            model=active_config.model,
            api_key_set=False,
            api_key_env=active_config.api_key_env,
            fixes=[],
        )

    prompt = _build_fix_prompt(root, scan, llm_review, fix_plan, sandbox_validation, repair_actions or [], max_files)
    active_client = client or OpenAICompatibleLLMClient(active_config)
    try:
        raw_response = active_client.generate(prompt)
    except Exception as exc:
        return LLMCodeFixReport(
            project_path=str(root),
            status="failed",
            applied=False,
            provider=active_config.provider,
            model=active_config.model,
            api_key_set=active_config.api_key_set,
            api_key_env=active_config.api_key_env,
            fixes=[],
            raw_response=str(exc),
        )
    fixes = _parse_fixes(raw_response, root, scan, apply_changes)
    status = "fixed" if apply_changes and fixes else "planned"
    if not fixes:
        status = "no_fixes"
    return LLMCodeFixReport(
        project_path=str(root),
        status=status,
        applied=apply_changes,
        provider=active_config.provider,
        model=active_config.model,
        api_key_set=active_config.api_key_set,
        api_key_env=active_config.api_key_env,
        fixes=fixes,
        raw_response=raw_response,
    )


def _build_fix_prompt(
    root: Path,
    scan: RepositoryScanResult,
    llm_review: LLMCodeReviewReport | None,
    fix_plan: LLMFixPlan | None,
    sandbox_validation: SandboxValidationReport | None,
    repair_actions: list[str],
    max_files: int,
) -> LLMTestPrompt:
    user_parts = [
        "Fix the Python source code issues identified by the review and sandbox results.",
        "Return JSON only with this shape:",
        '{"fixes":[{"file_path":"relative/path.py","summary":"...","replacement_content":"complete file content"}]}',
        "Rules:",
        "- Only propose replacements for files included in Source context.",
        "- replacement_content must be the complete new content of that file.",
        "- Do not include markdown fences.",
        "- Preserve public APIs unless a review finding requires a safer behavior.",
        "",
        "Selected fix plan:",
        _format_fix_plan(fix_plan),
        "",
        "Selected LLM review findings:",
        _format_findings(selected_findings(llm_review, fix_plan)),
        "",
        "Latest sandbox result:",
        _format_sandbox(sandbox_validation),
        "",
        "Repair actions:",
        "\n".join(f"- {item}" for item in repair_actions) or "- none",
        "",
        "Source context:",
        _collect_source_context(root, scan, max_files),
    ]
    return LLMTestPrompt(
        system=(
            "You are Software Engineer Agent Code Fix Agent. Produce minimal, safe Python fixes. "
            "Return valid JSON only and never include secrets."
        ),
        user="\n".join(user_parts),
        covered_functions=scan.source_files[:max_files],
    )


def _format_fix_plan(plan: LLMFixPlan | None) -> str:
    if plan is None or not plan.targets:
        return "- no selected targets"
    lines = [f"- status: {plan.status}", f"- rationale: {plan.rationale}", "- ordered targets:"]
    for target in plan.targets:
        lines.append(
            f"  - #{target.finding_index} {target.file_path}:{target.line} "
            f"[{target.severity}] {target.rule}; reason: {target.reason}"
        )
    return "\n".join(lines)


def _format_findings(findings: list[ReviewFinding]) -> str:
    if not findings:
        return "- none"
    lines: list[str] = []
    for finding in findings:
        lines.append(
            f"- {finding.file_path}:{finding.line} [{finding.severity}] "
            f"{finding.message} Suggestion: {finding.suggestion}"
        )
    return "\n".join(lines)


def _format_sandbox(report: SandboxValidationReport | None) -> str:
    if report is None:
        return "- not run"
    lines = [
        f"- status: {report.status}",
        f"- pytest: {report.analysis.passed}/{report.analysis.total} passed",
    ]
    if report.diagnosis.suggestions:
        lines.append("- suggestions:")
        lines.extend(f"  - {item}" for item in report.diagnosis.suggestions)
    stdout = report.execution.stdout.strip()
    if stdout:
        lines.append("- stdout excerpt:")
        lines.append(stdout[:2000])
    stderr = report.execution.stderr.strip()
    if stderr:
        lines.append("- stderr excerpt:")
        lines.append(stderr[:2000])
    return "\n".join(lines)


def _collect_source_context(root: Path, scan: RepositoryScanResult, max_files: int) -> str:
    chunks: list[str] = []
    for relative_file in scan.source_files[:max_files]:
        path = root / relative_file
        if not path.exists():
            continue
        chunks.append(f"# {relative_file}\n{path.read_text(encoding='utf-8')}")
    combined = "\n\n".join(chunks)
    if len(combined) > MAX_SOURCE_CHARS:
        return combined[:MAX_SOURCE_CHARS] + "\n# ... truncated ..."
    return combined


def _parse_fixes(raw_response: str, root: Path, scan: RepositoryScanResult, apply_changes: bool) -> list[LLMCodeFix]:
    payload_text = _extract_json(raw_response)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return []

    allowed_files = set(scan.source_files)
    fixes: list[LLMCodeFix] = []
    for item in payload.get("fixes", []):
        if not isinstance(item, dict):
            continue
        relative_file = str(item.get("file_path", "")).replace("\\", "/").strip()
        replacement = str(item.get("replacement_content", ""))
        summary = str(item.get("summary", "")).strip()[:500]
        if relative_file not in allowed_files or not relative_file.endswith(".py") or not replacement.strip():
            continue
        target = (root / relative_file).resolve()
        if not _is_relative_to(target, root):
            continue
        applied = False
        if apply_changes:
            target.write_text(replacement.rstrip() + "\n", encoding="utf-8")
            applied = True
        fixes.append(
            LLMCodeFix(
                file_path=relative_file,
                summary=summary,
                replacement_content=replacement,
                applied=applied,
            )
        )
    return fixes


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
