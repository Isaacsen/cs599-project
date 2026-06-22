from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

PYTHON_CONFIG_FILES = {
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
    "pytest.ini",
    ".coveragerc",
}

DEPENDENCY_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
    "environment.yml",
}


@dataclass(frozen=True)
class RepositoryScanIssue:
    severity: str
    message: str
    path: str = ""


@dataclass(frozen=True)
class RepositoryScanResult:
    project_path: str
    language: str
    test_framework: str
    source_files: list[str]
    test_files: list[str]
    status: str = "scanned"
    error_summary: str = ""
    config_files: list[str] | None = None
    dependency_files: list[str] | None = None
    package_roots: list[str] | None = None
    entry_points: list[str] | None = None
    issues: list[RepositoryScanIssue] | None = None

    @property
    def source_file_count(self) -> int:
        return len(self.source_files)

    @property
    def test_file_count(self) -> int:
        return len(self.test_files)


def scan_repository_agent(project_path: str | Path) -> RepositoryScanResult:
    root = Path(project_path).resolve()
    try:
        return _scan_existing_repository(root)
    except Exception as exc:
        return RepositoryScanResult(
            project_path=str(root),
            language="unknown",
            test_framework="unknown",
            source_files=[],
            test_files=[],
            status="failed",
            error_summary=f"{type(exc).__name__}: {exc}",
            config_files=[],
            dependency_files=[],
            package_roots=[],
            entry_points=[],
            issues=[
                RepositoryScanIssue(
                    severity="high",
                    message="Repository scan failed before source discovery completed.",
                    path=str(root),
                )
            ],
        )


def scan_repository(project_path: str | Path) -> RepositoryScanResult:
    result = scan_repository_agent(project_path)
    if result.status == "failed":
        raise FileNotFoundError(result.error_summary)
    return result


def _scan_existing_repository(root: Path) -> RepositoryScanResult:
    if not root.exists():
        raise FileNotFoundError(f"Project path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {root}")

    python_files = sorted(_iter_python_files(root))
    test_files = [path for path in python_files if _is_test_file(path)]
    source_files = [path for path in python_files if path not in test_files]
    config_files = _find_named_files(root, PYTHON_CONFIG_FILES)
    dependency_files = _find_named_files(root, DEPENDENCY_FILES)
    package_roots = _find_package_roots(root, source_files)
    entry_points = _find_entry_points(root)
    issues = _scan_issues(source_files, test_files, dependency_files)

    return RepositoryScanResult(
        project_path=str(root),
        language="Python" if python_files else "unknown",
        test_framework=_detect_test_framework(test_files, config_files),
        source_files=[_to_relative(root, path) for path in source_files],
        test_files=[_to_relative(root, path) for path in test_files],
        status="scanned",
        error_summary="",
        config_files=[_to_relative(root, path) for path in config_files],
        dependency_files=[_to_relative(root, path) for path in dependency_files],
        package_roots=[_to_relative(root, path) for path in package_roots],
        entry_points=[_to_relative(root, path) for path in entry_points],
        issues=issues,
    )


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def _find_named_files(root: Path, names: set[str]) -> list[Path]:
    matches: list[Path] = []
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.name in names:
            matches.append(path)
    return sorted(matches)


def _find_package_roots(root: Path, source_files: list[Path]) -> list[Path]:
    roots = {path.parent for path in source_files if (path.parent / "__init__.py").exists()}
    return sorted(roots)


def _find_entry_points(root: Path) -> list[Path]:
    candidates = []
    for name in ("main.py", "app.py", "cli.py", "__main__.py"):
        candidates.extend(path for path in root.rglob(name) if not _is_ignored(root, path))
    return sorted(set(candidates))


def _scan_issues(
    source_files: list[Path],
    test_files: list[Path],
    dependency_files: list[Path],
) -> list[RepositoryScanIssue]:
    issues: list[RepositoryScanIssue] = []
    if not source_files:
        issues.append(RepositoryScanIssue(severity="high", message="No Python source files were discovered."))
    if source_files and not test_files:
        issues.append(RepositoryScanIssue(severity="medium", message="No pytest-style test files were discovered."))
    if source_files and not dependency_files:
        issues.append(RepositoryScanIssue(severity="low", message="No standard Python dependency file was discovered."))
    return issues


def _detect_test_framework(test_files: list[Path], config_files: list[Path]) -> str:
    if test_files:
        return "pytest"
    if any(path.name in {"pytest.ini", "tox.ini"} for path in config_files):
        return "pytest"
    return "unknown"


def _is_ignored(root: Path, path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.relative_to(root).parts)


def _is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _to_relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
