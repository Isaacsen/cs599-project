from __future__ import annotations

import json
import re
import ast
import hashlib
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
class PatchSafetyReview:
    passed: bool
    violations: list[str]

    @property
    def violation_count(self) -> int:
        return len(self.violations)


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
    patch_review: PatchSafetyReview | None = None
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
    fixes = _parse_fixes(raw_response, root, scan)
    patch_review = _review_patch_safety(root, fixes)
    if apply_changes and patch_review.passed:
        _apply_fixes(root, fixes)
        fixes = [
            LLMCodeFix(
                file_path=fix.file_path,
                summary=fix.summary,
                replacement_content=fix.replacement_content,
                applied=True,
            )
            for fix in fixes
        ]
    status = "fixed" if apply_changes and fixes and patch_review.passed else "planned"
    if not fixes:
        status = "no_fixes"
    if fixes and not patch_review.passed:
        status = "patch_review_failed"
    return LLMCodeFixReport(
        project_path=str(root),
        status=status,
        applied=apply_changes,
        provider=active_config.provider,
        model=active_config.model,
        api_key_set=active_config.api_key_set,
        api_key_env=active_config.api_key_env,
        fixes=fixes,
        patch_review=patch_review,
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
        "请根据代码审查结果和 sandbox 结果修复 Python 源码问题。",
        "只返回 JSON，不要使用 Markdown 代码块。JSON key 必须保持英文，summary 必须使用中文。",
        "返回格式必须严格符合：",
        '{"fixes":[{"file_path":"relative/path.py","summary":"...","replacement_content":"complete file content"}]}',
        "规则：",
        "- 只能修改 Source context 中出现的文件。",
        "- replacement_content 必须是该文件修复后的完整内容，而不是 diff。",
        "- 不要包含 Markdown 代码块。",
        "- 除非 review finding 明确要求更安全的行为，否则保持 public API 不变。",
        "- Python 代码必须语法正确；代码注释可以使用中文。",
        "",
        "本轮修复计划：",
        _format_fix_plan(fix_plan),
        "",
        "本轮选中的 LLM 审查 findings：",
        _format_findings(selected_findings(llm_review, fix_plan)),
        "",
        "最近一次 sandbox 结果：",
        _format_sandbox(sandbox_validation),
        "",
        "Repair loop 建议动作：",
        "\n".join(f"- {item}" for item in repair_actions) or "- none",
        "",
        "源码上下文：",
        _collect_source_context(root, scan, max_files),
    ]
    return LLMTestPrompt(
        system=(
            "你是 Software Engineer Agent 的代码修复 Agent。"
            "请生成最小、可靠、安全的 Python 修复，并用中文概括每个修复。"
            "只返回合法 JSON，绝不要输出或编造密钥。"
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


def _parse_fixes(raw_response: str, root: Path, scan: RepositoryScanResult) -> list[LLMCodeFix]:
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
        fixes.append(
            LLMCodeFix(
                file_path=relative_file,
                summary=summary,
                replacement_content=replacement,
                applied=False,
            )
        )
    return fixes


def _review_patch_safety(root: Path, fixes: list[LLMCodeFix]) -> PatchSafetyReview:
    violations: list[str] = []
    for fix in fixes:
        original_path = root / fix.file_path
        original = original_path.read_text(encoding="utf-8") if original_path.exists() else ""
        replacement = fix.replacement_content
        try:
            original_tree = ast.parse(original or "\n")
            replacement_tree = ast.parse(replacement)
        except SyntaxError as exc:
            violations.append(f"{fix.file_path}: replacement has syntax error: {exc.msg}")
            continue
        missing_functions = _public_functions(original_tree) - _public_functions(replacement_tree)
        for function_name in sorted(missing_functions):
            violations.append(f"{fix.file_path}: public function removed: {function_name}")
        violations.extend(f"{fix.file_path}: {item}" for item in _dangerous_constructs(replacement_tree))
    return PatchSafetyReview(passed=not violations, violations=violations[:20])


def _apply_fixes(root: Path, fixes: list[LLMCodeFix]) -> None:
    for fix in fixes:
        target = (root / fix.file_path).resolve()
        if _is_relative_to(target, root):
            target.write_text(fix.replacement_content.rstrip() + "\n", encoding="utf-8")


def _public_functions(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    }


def _dangerous_constructs(tree: ast.AST) -> list[str]:
    violations: list[str] = []
    dangerous_imports = {"subprocess", "socket", "shutil"}
    dangerous_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in dangerous_imports:
                    violations.append(f"dangerous import: {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in dangerous_imports:
            violations.append(f"dangerous import: {node.module}")
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in dangerous_calls or call_name in {"os.system", "subprocess.run", "subprocess.Popen"}:
                violations.append(f"dangerous call: {call_name}")
    return violations


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def replacement_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
