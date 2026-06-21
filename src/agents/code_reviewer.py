from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from src.tools.repo_scanner import RepositoryScanResult


DANGEROUS_CALLS = {"eval", "exec", "__import__"}
SECRET_NAME_PATTERN = re.compile(r"(api[_-]?key|secret|token|password)", re.IGNORECASE)
SECRET_VALUE_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,})"
)
LONG_FUNCTION_LINES = 50


@dataclass(frozen=True)
class ReviewFinding:
    file_path: str
    line: int
    severity: str
    rule: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class ReviewReport:
    project_path: str
    findings: list[ReviewFinding]

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def high_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "low")


def review_repository(project_path: str | Path, scan: RepositoryScanResult) -> ReviewReport:
    root = Path(project_path).resolve()
    test_text = _collect_test_text(root, scan.test_files)
    findings: list[ReviewFinding] = []

    for relative_file in scan.source_files:
        path = root / relative_file
        tree = ast.parse(path.read_text(encoding="utf-8"))
        findings.extend(_review_tree(relative_file, tree, test_text))

    findings.sort(key=lambda item: (item.file_path, item.line, item.rule))
    return ReviewReport(project_path=str(root), findings=findings)


def format_review_report(report: ReviewReport) -> str:
    lines = [
        "[Software Engineer Agent Code Review]",
        "",
        f"Project: {report.project_path}",
        f"Findings: {report.finding_count}",
        f"High: {report.high_count}",
        f"Medium: {report.medium_count}",
        f"Low: {report.low_count}",
    ]

    if report.findings:
        lines.append("")
        lines.append("Findings:")
        for finding in report.findings:
            lines.extend(
                [
                    f"- [{finding.severity}] {finding.rule} at {finding.file_path}:{finding.line}",
                    f"  {finding.message}",
                    f"  Suggestion: {finding.suggestion}",
                ]
            )
    return "\n".join(lines)


def _review_tree(relative_file: str, tree: ast.AST, test_text: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            findings.extend(_review_function(relative_file, node, test_text))
        elif isinstance(node, ast.Call):
            findings.extend(_review_call(relative_file, node))
        elif isinstance(node, ast.ExceptHandler):
            findings.extend(_review_exception_handler(relative_file, node))
        elif isinstance(node, ast.Assign):
            findings.extend(_review_assignment(relative_file, node))
    return findings


def _review_function(relative_file: str, node: ast.FunctionDef, test_text: str) -> list[ReviewFinding]:
    if node.name.startswith("_"):
        return []

    findings: list[ReviewFinding] = []
    function_lines = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
    if function_lines > LONG_FUNCTION_LINES:
        findings.append(
            ReviewFinding(
                file_path=relative_file,
                line=node.lineno,
                severity="low",
                rule="long_function",
                message=f"Function '{node.name}' has {function_lines} lines.",
                suggestion="Split the function into smaller units before adding generated tests.",
            )
        )

    if not _has_test_reference(node.name, test_text):
        findings.append(
            ReviewFinding(
                file_path=relative_file,
                line=node.lineno,
                severity="medium",
                rule="missing_test",
                message=f"Public function '{node.name}' is not referenced by existing tests.",
                suggestion="Generate or add pytest coverage for the public function.",
            )
        )

    if _contains_division(node) and not _has_zero_division_test(node.name, test_text) and not _has_zero_division_guard(node):
        findings.append(
            ReviewFinding(
                file_path=relative_file,
                line=node.lineno,
                severity="medium",
                rule="division_risk",
                message=f"Function '{node.name}' performs division without an obvious zero-division test.",
                suggestion="Add a boundary test for denominator zero or document the expected exception.",
            )
        )
    return findings


def _review_call(relative_file: str, node: ast.Call) -> list[ReviewFinding]:
    call_name = _call_name(node)
    if call_name in DANGEROUS_CALLS or call_name.startswith("subprocess."):
        return [
            ReviewFinding(
                file_path=relative_file,
                line=node.lineno,
                severity="high",
                rule="dangerous_call",
                message=f"Dangerous call '{call_name}' was found.",
                suggestion="Remove the call or isolate it behind a safe, reviewed tool interface.",
            )
        ]
    return []


def _review_exception_handler(relative_file: str, node: ast.ExceptHandler) -> list[ReviewFinding]:
    if node.type is None:
        exception_name = "bare except"
    elif isinstance(node.type, ast.Name):
        exception_name = node.type.id
    else:
        exception_name = ""

    if exception_name in {"bare except", "Exception"}:
        return [
            ReviewFinding(
                file_path=relative_file,
                line=node.lineno,
                severity="medium",
                rule="broad_exception",
                message=f"Broad exception handler '{exception_name}' can hide real failures.",
                suggestion="Catch a narrower exception type and keep the error observable.",
            )
        ]
    return []


def _review_assignment(relative_file: str, node: ast.Assign) -> list[ReviewFinding]:
    target_names = [_target_name(target) for target in node.targets]
    value = node.value.value if isinstance(node.value, ast.Constant) else None
    if not isinstance(value, str) or not value:
        return []

    name_suspicious = any(SECRET_NAME_PATTERN.search(name or "") for name in target_names)
    value_suspicious = bool(SECRET_VALUE_PATTERN.search(value))
    if name_suspicious or value_suspicious:
        return [
            ReviewFinding(
                file_path=relative_file,
                line=node.lineno,
                severity="high",
                rule="hardcoded_secret",
                message="Possible hardcoded secret was found in source code.",
                suggestion="Move secrets to environment variables and keep only placeholders in the repository.",
            )
        ]
    return []


def _collect_test_text(root: Path, test_files: list[str]) -> str:
    chunks: list[str] = []
    for relative_file in test_files:
        path = root / relative_file
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _has_test_reference(function_name: str, test_text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(function_name)}\b", test_text))


def _has_zero_division_test(function_name: str, test_text: str) -> bool:
    return _has_test_reference(function_name, test_text) and "ZeroDivisionError" in test_text


def _contains_division(node: ast.FunctionDef) -> bool:
    return any(isinstance(child, ast.BinOp) and isinstance(child.op, ast.Div) for child in ast.walk(node))


def _has_zero_division_guard(node: ast.FunctionDef) -> bool:
    return any(_raises_zero_division(child) for child in ast.walk(node))


def _raises_zero_division(node: ast.AST) -> bool:
    if not isinstance(node, ast.Raise):
        return False
    exc = node.exc
    if isinstance(exc, ast.Name):
        return exc.id == "ZeroDivisionError"
    if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
        return exc.func.id == "ZeroDivisionError"
    return False


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return ""


def _target_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
