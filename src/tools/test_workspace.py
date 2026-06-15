from __future__ import annotations

import shutil
from pathlib import Path

from src.agents.test_generator import GeneratedTestSuite
from src.tools.repo_scanner import IGNORED_DIRS


def copy_project_with_generated_tests(
    source_project: str | Path,
    workspace_root: str | Path,
    suite: GeneratedTestSuite,
) -> Path:
    source = Path(source_project).resolve()
    destination = Path(workspace_root).resolve() / "project"

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(*IGNORED_DIRS),
    )

    generated_dir = destination / "tests"
    generated_dir.mkdir(exist_ok=True)
    generated_file = generated_dir / suite.test_file_name
    generated_file.write_text(suite.content, encoding="utf-8")

    return destination
