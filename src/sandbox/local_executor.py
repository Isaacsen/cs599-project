from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestExecutionResult:
    passed: bool
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    executor: str = "local"


def run_pytest(project_path: str | Path, timeout_seconds: int = 30) -> TestExecutionResult:
    root = Path(project_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project path does not exist: {root}")

    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "."],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - started_at
        return TestExecutionResult(
            passed=False,
            exit_code=None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"pytest timed out after {timeout_seconds} seconds",
            duration_seconds=duration,
            timed_out=True,
            executor="local",
        )

    duration = time.perf_counter() - started_at
    return TestExecutionResult(
        passed=completed.returncode == 0,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=duration,
        timed_out=False,
        executor="local",
    )
