import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.tools.software_engineer_graph_writer import software_engineer_graph_result_to_dict
from src.workflow.software_engineer_graph import run_software_engineer_graph


LLM_RESPONSE = """```python
import pytest

import risky_module as risky_module


def test_risky_module_divide_llm():
    assert risky_module.divide(4, 2) == 2
    with pytest.raises(ZeroDivisionError):
        risky_module.divide(1, 0)
```"""


class SoftwareEngineerGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name) / "review_target"
        shutil.copytree("examples/review_target", self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_runs_graph_dry_run_without_writing_source(self) -> None:
        source_file = self.project_path / "risky_module.py"
        original_content = source_file.read_text(encoding="utf-8")

        result = run_software_engineer_graph(self.project_path)

        self.assertEqual("completed", result.state["status"])
        self.assertIn(result.graph_runtime, {"langgraph", "fallback"})
        self.assertEqual(["scan", "review", "fix", "unit_tests", "finish"], result.node_trace)
        self.assertEqual(7, result.finding_count)
        self.assertEqual(6, result.fix_edit_count)
        self.assertEqual(3, result.generated_unit_test_count)
        self.assertEqual(original_content, source_file.read_text(encoding="utf-8"))
        self.assertFalse((self.project_path / "tests" / "test_testguard_generated.py").exists())

    def test_runs_llm_branch_with_mock_response(self) -> None:
        result = run_software_engineer_graph(
            self.project_path,
            use_llm_tests=True,
            mock_llm_response=LLM_RESPONSE,
        )

        self.assertEqual(
            ["scan", "review", "fix", "unit_tests", "llm_tests", "finish"],
            result.node_trace,
        )
        self.assertEqual(3, result.generated_llm_test_count)
        self.assertTrue(result.state["llm_tests"].security_check.passed)

    def test_graph_report_does_not_include_api_key_value(self) -> None:
        result = run_software_engineer_graph(
            self.project_path,
            use_llm_tests=True,
            mock_llm_response=LLM_RESPONSE,
        )
        data = software_engineer_graph_result_to_dict(result)
        serialized = json.dumps(data)

        self.assertIn("summary", data)
        self.assertIn("llm_tests", data)
        self.assertNotIn("unit-test-secret", serialized)
        self.assertNotIn("LLM_API_KEY=", serialized)


if __name__ == "__main__":
    unittest.main()
