from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.bug_fixer import FixPlan
from src.tools.repo_scanner import RepositoryScanResult


SAFE_FIX_RULES = {
    "dangerous_eval_fix",
    "hardcoded_secret_fix",
    "broad_exception_fix",
    "division_guard_fix",
    "support_import_fix",
}
DANGEROUS_PATTERN = re.compile(r"\b(subprocess|socket|requests|exec|__import__)\b|(?<!literal_)\beval\s*\(")


@dataclass(frozen=True)
class PatchReviewFinding:
    file_path: str
    line: int
    severity: str
    rule: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class PatchReviewReport:
    project_path: str
    status: str
    findings: list[PatchReviewFinding]

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def passed(self) -> bool:
        return not any(finding.severity == "high" for finding in self.findings)


def review_fix_plan(project_path: str | Path, scan: RepositoryScanResult, fix_plan: FixPlan) -> PatchReviewReport:
    root = Path(project_path).resolve()
    source_files = set(scan.source_files)
    findings: list[PatchReviewFinding] = []

    for edit in fix_plan.edits:
        if edit.file_path not in source_files:
            findings.append(
                PatchReviewFinding(
                    file_path=edit.file_path,
                    line=edit.line,
                    severity="high",
                    rule="patch_outside_source",
                    message="Fix edit targets a file outside the scanned source set.",
                    suggestion="Reject this patch or rescan the project before applying it.",
                )
            )
        if edit.rule not in SAFE_FIX_RULES:
            findings.append(
                PatchReviewFinding(
                    file_path=edit.file_path,
                    line=edit.line,
                    severity="medium",
                    rule="unknown_fix_rule",
                    message=f"Fix rule '{edit.rule}' is not in the approved safe-fix list.",
                    suggestion="Review this edit manually before applying it.",
                )
            )
        if DANGEROUS_PATTERN.search(edit.after):
            findings.append(
                PatchReviewFinding(
                    file_path=edit.file_path,
                    line=edit.line,
                    severity="high",
                    rule="dangerous_patch_content",
                    message="Patch output contains a dangerous token.",
                    suggestion="Reject the patch and regenerate a safer fix.",
                )
            )

    for relative_file in source_files:
        path = root / relative_file
        if path.exists():
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                findings.append(
                    PatchReviewFinding(
                        file_path=relative_file,
                        line=exc.lineno or 1,
                        severity="high",
                        rule="syntax_error_after_patch",
                        message=str(exc),
                        suggestion="Fix syntax errors before running generated tests.",
                    )
                )

    status = "passed" if not findings else "needs_review"
    return PatchReviewReport(project_path=str(root), status=status, findings=findings)
