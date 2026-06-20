import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.llm_test_generator import generate_llm_pytest_tests
from src.llm.client import _chat_completions_url, _extract_chat_content
from src.llm.config import LLMConfig
from src.tools.llm_test_writer import llm_test_report_to_dict
from src.tools.repo_scanner import scan_repository


LLM_RESPONSE = """```python
import pytest

import calculator as calculator


def test_calculator_add_llm():
    assert calculator.add(1, 2) == 3


def test_calculator_divide_llm():
    assert calculator.divide(4, 2) == 2
    with pytest.raises(ZeroDivisionError):
        calculator.divide(1, 0)
```"""


class FakeLLMClient:
    def __init__(self, content: str) -> None:
        self.content = content

    def generate(self, prompt) -> str:
        return self.content


class LLMTestGeneratorAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name) / "sample_python_project"
        shutil.copytree("examples/sample_python_project", self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_skips_without_api_key_or_injected_client(self) -> None:
        scan = scan_repository(self.project_path)
        with patch.dict("os.environ", {}, clear=True):
            report = generate_llm_pytest_tests(self.project_path, scan)

        self.assertEqual("skipped_missing_api_key", report.status)
        self.assertFalse(report.applied)
        self.assertIsNone(report.suite)
        self.assertIsNone(report.security_check)
        self.assertEqual(0, report.generated_test_count)

    def test_generates_tests_with_injected_llm_client(self) -> None:
        scan = scan_repository(self.project_path)
        report = generate_llm_pytest_tests(
            self.project_path,
            scan,
            client=FakeLLMClient(LLM_RESPONSE),
        )

        self.assertEqual("generated", report.status)
        self.assertFalse(report.applied)
        self.assertTrue(report.security_check.passed)
        self.assertEqual(2, report.generated_test_count)
        self.assertIn("test_calculator_add_llm", report.suite.content)
        self.assertEqual(["calculator.add", "calculator.divide"], report.suite.covered_functions)

    def test_applies_generated_tests(self) -> None:
        scan = scan_repository(self.project_path)
        report = generate_llm_pytest_tests(
            self.project_path,
            scan,
            apply_changes=True,
            client=FakeLLMClient(LLM_RESPONSE),
        )
        target_file = self.project_path / report.test_file_path

        self.assertTrue(report.applied)
        self.assertTrue(target_file.exists())
        self.assertEqual(report.suite.content, target_file.read_text(encoding="utf-8"))

    def test_report_dict_does_not_include_api_key_value(self) -> None:
        scan = scan_repository(self.project_path)
        config = LLMConfig(
            provider="dashscope",
            model="glm-5.2",
            api_key_set=True,
            api_key_env="DASHSCOPE_API_KEY",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        report = generate_llm_pytest_tests(
            self.project_path,
            scan,
            client=FakeLLMClient(LLM_RESPONSE),
            config=config,
        )
        data = llm_test_report_to_dict(report)
        serialized = json.dumps(data)

        self.assertEqual("DASHSCOPE_API_KEY", data["llm_config"]["api_key_env"])
        self.assertNotIn("unit-test-secret", serialized)
        self.assertNotIn("LLM_API_KEY", serialized)

    def test_chat_response_helpers(self) -> None:
        self.assertEqual(
            "https://api.deepseek.com/chat/completions",
            _chat_completions_url("https://api.deepseek.com"),
        )
        self.assertEqual(
            "print('ok')",
            _extract_chat_content({"choices": [{"message": {"content": "print('ok')"}}]}),
        )


if __name__ == "__main__":
    unittest.main()
