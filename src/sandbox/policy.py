from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SandboxPolicy:
    image: str = "testguard-python:latest"
    network_enabled: bool = False
    readonly_source: bool = True
    timeout_seconds: int = 30
    cpu_limit: str = "1"
    memory_limit: str = "512m"
    pids_limit: int = 128
    tmpfs_size: str = "128m"
    workdir: str = "/workspace"
    forbidden_modules: tuple[str, ...] = field(
        default_factory=lambda: (
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
        )
    )

    def docker_network_arg(self) -> str:
        return "bridge" if self.network_enabled else "none"

    def source_mount_mode(self) -> str:
        return "ro" if self.readonly_source else "rw"
