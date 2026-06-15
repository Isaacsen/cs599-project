from pathlib import Path
import unittest

from src.sandbox.docker_executor import _build_docker_command
from src.sandbox.policy import SandboxPolicy


class DockerSandboxCommandTest(unittest.TestCase):
    def test_docker_command_contains_isolation_flags(self) -> None:
        command = _build_docker_command(
            Path("examples/sample_python_project").resolve(),
            SandboxPolicy(timeout_seconds=10),
            container_name="testguard-test",
        )
        joined = " ".join(command)

        self.assertIn("--name testguard-test", joined)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("--security-opt no-new-privileges", joined)
        self.assertIn("--memory 512m", joined)
        self.assertIn("--pids-limit 128", joined)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", command)
        self.assertIn("PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", command)
        self.assertIn("--mount", command)
        self.assertTrue(any("target=/workspace" in part for part in command))
        self.assertTrue(any("readonly" in part for part in command))


if __name__ == "__main__":
    unittest.main()
