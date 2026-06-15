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


@dataclass(frozen=True)
class RepositoryScanResult:
    project_path: str
    language: str
    test_framework: str
    source_files: list[str]
    test_files: list[str]


def scan_repository(project_path: str | Path) -> RepositoryScanResult:
    root = Path(project_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {root}")

    python_files = sorted(_iter_python_files(root))
    test_files = [path for path in python_files if _is_test_file(path)]
    source_files = [path for path in python_files if path not in test_files]

    return RepositoryScanResult(
        project_path=str(root),
        language="Python",
        test_framework="pytest",
        source_files=[_to_relative(root, path) for path in source_files],
        test_files=[_to_relative(root, path) for path in test_files],
    )


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _to_relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
