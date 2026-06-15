from __future__ import annotations

import ast
from dataclasses import dataclass


FORBIDDEN_IMPORTS = {
    "os",
    "pathlib",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}
FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "open",
    "__import__",
}


@dataclass(frozen=True)
class SecurityViolation:
    rule: str
    detail: str
    line: int


@dataclass(frozen=True)
class SecurityCheckResult:
    passed: bool
    violations: list[SecurityViolation]

    @property
    def violation_count(self) -> int:
        return len(self.violations)


def check_generated_test_code(content: str) -> SecurityCheckResult:
    tree = ast.parse(content)
    violations: list[SecurityViolation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0]
                if root_name in FORBIDDEN_IMPORTS:
                    violations.append(
                        SecurityViolation(
                            rule="forbidden_import",
                            detail=root_name,
                            line=node.lineno,
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            root_name = (node.module or "").split(".", 1)[0]
            if root_name in FORBIDDEN_IMPORTS:
                violations.append(
                    SecurityViolation(
                        rule="forbidden_import",
                        detail=root_name,
                        line=node.lineno,
                    )
                )
        elif isinstance(node, ast.Call):
            call_name = _call_name(node)
            if call_name in FORBIDDEN_CALLS:
                violations.append(
                    SecurityViolation(
                        rule="forbidden_call",
                        detail=call_name,
                        line=node.lineno,
                    )
                )

    return SecurityCheckResult(passed=not violations, violations=violations)


def assert_generated_test_code_is_safe(content: str) -> None:
    result = check_generated_test_code(content)
    if result.passed:
        return
    details = ", ".join(f"{item.rule}:{item.detail}@{item.line}" for item in result.violations)
    raise ValueError(f"Generated tests failed security check: {details}")


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""
