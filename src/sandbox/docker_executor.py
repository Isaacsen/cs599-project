from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from pathlib import Path

from src.sandbox.local_executor import TestExecutionResult
from src.sandbox.policy import SandboxPolicy


def run_pytest_in_docker(
    project_path: str | Path,
    policy: SandboxPolicy | None = None,
) -> TestExecutionResult:
    root = Path(project_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project path does not exist: {root}")
    if shutil.which("docker") is None:
        raise RuntimeError("Docker executable was not found. Install Docker or use --executor local.")

    active_policy = policy or SandboxPolicy()
    container_name = f"testguard-{uuid.uuid4().hex[:12]}"
    command = _build_docker_command(root, active_policy, container_name=container_name)

    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=active_policy.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - started_at
        _cleanup_container(container_name)
        return TestExecutionResult(
            passed=False,
            exit_code=None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"docker pytest timed out after {active_policy.timeout_seconds} seconds",
            duration_seconds=duration,
            timed_out=True,
            executor="docker",
        )

    duration = time.perf_counter() - started_at
    return TestExecutionResult(
        passed=completed.returncode == 0,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=duration,
        timed_out=False,
        executor="docker",
    )


def _build_docker_command(
    root: Path,
    policy: SandboxPolicy,
    container_name: str = "testguard-sandbox",
) -> list[str]:
    mount_options = [
        "type=bind",
        f"source={root}",
        f"target={policy.workdir}",
    ]
    if policy.readonly_source:
        mount_options.append("readonly")

    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--network",
        policy.docker_network_arg(),
        "--cpus",
        policy.cpu_limit,
        "--memory",
        policy.memory_limit,
        "--pids-limit",
        str(policy.pids_limit),
        "--read-only",
        "--tmpfs",
        f"/tmp:rw,size={policy.tmpfs_size}",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "--mount",
        ",".join(mount_options),
        "-w",
        policy.workdir,
        policy.image,
        "python",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        ".",
    ]


def _cleanup_container(container_name: str) -> None:
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
