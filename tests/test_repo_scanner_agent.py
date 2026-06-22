import tempfile
import unittest
from pathlib import Path

from src.agents.llm_code_reviewer import review_repository_with_llm
from src.agents.llm_test_generator import generate_llm_pytest_tests
from src.agents.repo_scanner import scan_repository_agent
from src.llm.config import LLMConfig


class FailingLLMClient:
    def generate(self, prompt) -> str:
        raise RuntimeError("unit test LLM failure")


class RepoScannerAgentTest(unittest.TestCase):
    def test_scans_real_project_metadata(self) -> None:
        report = scan_repository_agent("examples/sample_python_project")

        self.assertEqual("scanned", report.status)
        self.assertEqual("Python", report.language)
        self.assertEqual("pytest", report.test_framework)
        self.assertIn("calculator.py", report.source_files)
        self.assertIn("test_calculator.py", report.test_files)

    def test_returns_structured_failure_report(self) -> None:
        report = scan_repository_agent("does-not-exist-for-scan-agent")

        self.assertEqual("failed", report.status)
        self.assertEqual([], report.source_files)
        self.assertIn("FileNotFoundError", report.error_summary)
        self.assertTrue(report.issues)

    def test_llm_review_returns_structured_failure_report(self) -> None:
        scan = scan_repository_agent("examples/sample_python_project")
        config = LLMConfig(
            provider="dashscope",
            model="glm-5.2",
            api_key_set=True,
            api_key_env="DASHSCOPE_API_KEY",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        report = review_repository_with_llm(
            "examples/sample_python_project",
            scan,
            client=FailingLLMClient(),
            config=config,
        )

        self.assertEqual("failed", report.status)
        self.assertEqual([], report.findings)
        self.assertIn("unit test LLM failure", report.raw_response)

    def test_llm_tests_returns_structured_failure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sample"
            root.mkdir()
            (root / "sample.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            scan = scan_repository_agent(root)
            config = LLMConfig(
                provider="dashscope",
                model="glm-5.2",
                api_key_set=True,
                api_key_env="DASHSCOPE_API_KEY",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            report = generate_llm_pytest_tests(root, scan, client=FailingLLMClient(), config=config)

        self.assertEqual("failed", report.status)
        self.assertEqual(0, report.generated_test_count)
        self.assertIn("unit test LLM failure", report.error_summary)


if __name__ == "__main__":
    unittest.main()
