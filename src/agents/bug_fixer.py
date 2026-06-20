from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from src.tools.repo_scanner import RepositoryScanResult


SECRET_NAME_PATTERN = re.compile(r"(api[_-]?key|secret|token|password)", re.IGNORECASE)
SECRET_VALUE_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,})"
)


@dataclass(frozen=True)
class FixEdit:
    file_path: str
    line: int
    rule: str
    description: str
    before: str
    after: str


@dataclass(frozen=True)
class FixPlan:
    project_path: str
    applied: bool
    edits: list[FixEdit]

    @property
    def edit_count(self) -> int:
        return len(self.edits)

    @property
    def files_changed(self) -> int:
        return len({edit.file_path for edit in self.edits})


def fix_repository(
    project_path: str | Path,
    scan: RepositoryScanResult,
    apply_changes: bool = False,
) -> FixPlan:
    root = Path(project_path).resolve()
    edits: list[FixEdit] = []

    for relative_file in scan.source_files:
        path = root / relative_file
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        fixed_content, file_edits = _fix_python_source(relative_file, content, tree)
        edits.extend(file_edits)
        if apply_changes and fixed_content != content:
            path.write_text(fixed_content, encoding="utf-8")

    return FixPlan(project_path=str(root), applied=apply_changes, edits=edits)


def format_fix_plan(plan: FixPlan) -> str:
    lines = [
        "[TestGuard Bug Fix]",
        "",
        f"Project: {plan.project_path}",
        f"Applied: {plan.applied}",
        f"Edits: {plan.edit_count}",
        f"Files Changed: {plan.files_changed}",
    ]

    if plan.edits:
        lines.append("")
        lines.append("Edits:")
        for edit in plan.edits:
            lines.extend(
                [
                    f"- {edit.rule} at {edit.file_path}:{edit.line}",
                    f"  {edit.description}",
                    f"  Before: {edit.before}",
                    f"  After: {edit.after}",
                ]
            )
    return "\n".join(lines)


def _fix_python_source(relative_file: str, content: str, tree: ast.AST) -> tuple[str, list[FixEdit]]:
    lines = content.splitlines()
    replacements: dict[int, str] = {}
    insertions: dict[int, list[str]] = {}
    edits: list[FixEdit] = []
    required_imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == "eval":
            _replace_eval_call(relative_file, lines, replacements, edits, node)
            required_imports.add("ast")
        elif isinstance(node, ast.Assign):
            if _replace_hardcoded_secret(relative_file, lines, replacements, edits, node):
                required_imports.add("os")
        elif isinstance(node, ast.ExceptHandler):
            _narrow_broad_exception(relative_file, lines, replacements, edits, node)
        elif isinstance(node, ast.FunctionDef):
            _insert_division_guard(relative_file, lines, insertions, edits, node)

    _insert_required_imports(relative_file, lines, tree, insertions, edits, required_imports)
    fixed_content = _build_content(lines, replacements, insertions, content.endswith("\n"))
    return fixed_content, edits


def _replace_eval_call(
    relative_file: str,
    lines: list[str],
    replacements: dict[int, str],
    edits: list[FixEdit],
    node: ast.Call,
) -> None:
    line_no = node.lineno
    before = replacements.get(line_no, lines[line_no - 1])
    after = before.replace("eval(", "ast.literal_eval(")
    if before == after:
        return
    replacements[line_no] = after
    edits.append(
        FixEdit(
            file_path=relative_file,
            line=line_no,
            rule="dangerous_eval_fix",
            description="Replace eval with ast.literal_eval for safer literal parsing.",
            before=before.strip(),
            after=after.strip(),
        )
    )


def _replace_hardcoded_secret(
    relative_file: str,
    lines: list[str],
    replacements: dict[int, str],
    edits: list[FixEdit],
    node: ast.Assign,
) -> bool:
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return False
    value = node.value.value if isinstance(node.value, ast.Constant) else None
    if not isinstance(value, str) or not value:
        return False

    target_name = node.targets[0].id
    if not SECRET_NAME_PATTERN.search(target_name) and not SECRET_VALUE_PATTERN.search(value):
        return False

    line_no = node.lineno
    before = replacements.get(line_no, lines[line_no - 1])
    env_name = _env_name_for(target_name)
    after = f'{_indent_of(before)}{target_name} = os.getenv("{env_name}", "")'
    replacements[line_no] = after
    edits.append(
        FixEdit(
            file_path=relative_file,
            line=line_no,
            rule="hardcoded_secret_fix",
            description="Move the value behind an environment variable lookup.",
            before=before.strip(),
            after=after.strip(),
        )
    )
    return True


def _narrow_broad_exception(
    relative_file: str,
    lines: list[str],
    replacements: dict[int, str],
    edits: list[FixEdit],
    node: ast.ExceptHandler,
) -> None:
    if node.type is None:
        broad_exception = True
    elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
        broad_exception = True
    else:
        broad_exception = False
    if not broad_exception:
        return

    line_no = node.lineno
    before = replacements.get(line_no, lines[line_no - 1])
    after = f"{_indent_of(before)}except ValueError:"
    replacements[line_no] = after
    edits.append(
        FixEdit(
            file_path=relative_file,
            line=line_no,
            rule="broad_exception_fix",
            description="Narrow broad exception handling to ValueError for simple parsing failures.",
            before=before.strip(),
            after=after.strip(),
        )
    )


def _insert_division_guard(
    relative_file: str,
    lines: list[str],
    insertions: dict[int, list[str]],
    edits: list[FixEdit],
    node: ast.FunctionDef,
) -> None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Return):
            continue
        if not isinstance(child.value, ast.BinOp) or not isinstance(child.value.op, ast.Div):
            continue
        if not isinstance(child.value.right, ast.Name):
            continue

        denominator = child.value.right.id
        if _has_zero_division_guard(node, denominator):
            continue

        line_no = child.lineno
        before = lines[line_no - 1]
        indent = _indent_of(before)
        guard_lines = [
            f"{indent}if {denominator} == 0:",
            f'{indent}    raise ZeroDivisionError("division by zero")',
        ]
        existing = insertions.setdefault(line_no, [])
        if guard_lines[0] in existing:
            continue
        existing.extend(guard_lines)
        edits.append(
            FixEdit(
                file_path=relative_file,
                line=line_no,
                rule="division_guard_fix",
                description="Add an explicit zero-division guard before division.",
                before=before.strip(),
                after="\n".join([*guard_lines, before]).strip(),
            )
        )


def _insert_required_imports(
    relative_file: str,
    lines: list[str],
    tree: ast.AST,
    insertions: dict[int, list[str]],
    edits: list[FixEdit],
    required_imports: set[str],
) -> None:
    missing_imports = sorted(module for module in required_imports if not _has_import(tree, module))
    if not missing_imports:
        return

    insert_line = _import_insert_line(tree, lines)
    import_lines = [f"import {module}" for module in missing_imports]
    if insert_line <= len(lines) and lines[insert_line - 1].strip():
        import_lines.append("")

    insertions.setdefault(insert_line, [])
    for import_line in import_lines:
        if import_line not in insertions[insert_line]:
            insertions[insert_line].append(import_line)

    for module in missing_imports:
        edits.append(
            FixEdit(
                file_path=relative_file,
                line=insert_line,
                rule="support_import_fix",
                description=f"Add import required by automatic fix: {module}.",
                before="",
                after=f"import {module}",
            )
        )


def _build_content(
    lines: list[str],
    replacements: dict[int, str],
    insertions: dict[int, list[str]],
    had_trailing_newline: bool,
) -> str:
    output: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        output.extend(insertions.get(line_no, []))
        output.append(replacements.get(line_no, line))
    output.extend(insertions.get(len(lines) + 1, []))

    fixed = "\n".join(output)
    if had_trailing_newline or fixed:
        fixed += "\n"
    return fixed


def _has_import(tree: ast.AST, module_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == module_name for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module == module_name:
            return True
    return False


def _import_insert_line(tree: ast.AST, lines: list[str]) -> int:
    if not lines:
        return 1

    line_no = 1
    body = getattr(tree, "body", [])
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            line_no = (getattr(body[0], "end_lineno", body[0].lineno) or body[0].lineno) + 1

    while line_no <= len(lines):
        stripped = lines[line_no - 1].strip()
        if stripped.startswith("from __future__ ") or stripped.startswith("import ") or stripped.startswith("from "):
            line_no += 1
            continue
        if stripped == "":
            line_no += 1
            continue
        break
    return line_no


def _has_zero_division_guard(node: ast.FunctionDef, denominator: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.If) and _is_zero_check(child.test, denominator):
            if any(_raises_zero_division(item) for item in child.body):
                return True
    return False


def _is_zero_check(node: ast.AST, denominator: str) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    if not isinstance(node.left, ast.Name) or node.left.id != denominator:
        return False
    if not node.ops or not isinstance(node.ops[0], ast.Eq):
        return False
    if not node.comparators:
        return False
    comparator = node.comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == 0


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


def _env_name_for(name: str) -> str:
    parts = re.sub(r"[^A-Za-z0-9]+", "_", name).upper().strip("_")
    return parts or "TESTGUARD_SECRET"


def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]
