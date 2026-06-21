import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.llm_test_generator import LLMTestGenerationReport
from src.agents.security_checker import check_generated_test_code
from src.agents.test_generator import GeneratedTestSuite
from src.agents.test_planner import plan_tests
from src.llm.config import LLMConfig
from src.llm.prompt_builder import build_test_generation_prompt
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


def _fake_llm_generation(project_path, scan, apply_changes=False, test_file_path="tests/test_software_engineer_llm_generated.py", max_functions=8):
    root = Path(project_path).resolve()
    test_plan = plan_tests(root, scan, max_functions=max_functions)
    prompt = build_test_generation_prompt(root, test_plan)
    test_content = "\n".join(LLM_RESPONSE.splitlines()[1:-1]).strip() + "\n"
    security_check = check_generated_test_code(test_content)
    return LLMTestGenerationReport(
        project_path=str(root),
        status="generated",
        applied=apply_changes,
        provider="dashscope",
        model="glm-5.2",
        api_key_set=True,
        api_key_env="DASHSCOPE_API_KEY",
        test_file_path=str(test_file_path),
        prompt=prompt,
        test_plan=test_plan,
        suite=GeneratedTestSuite(
            test_file_name=Path(test_file_path).name,
            content=test_content,
            covered_functions=prompt.covered_functions,
        ),
        security_check=security_check,
    )


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
        self.assertEqual(
            ["scan", "review", "fix", "patch_review", "unit_tests", "coverage_feedback", "finish"],
            result.node_trace,
        )
        self.assertEqual(7, result.finding_count)
        self.assertEqual(6, result.fix_edit_count)
        self.assertEqual(3, result.generated_unit_test_count)
        self.assertEqual(original_content, source_file.read_text(encoding="utf-8"))
        self.assertFalse((self.project_path / "tests" / "test_software_engineer_generated.py").exists())

    def test_runs_llm_branch_with_injected_generation(self) -> None:
        with patch(
            "src.workflow.software_engineer_graph.generate_llm_pytest_tests",
            side_effect=_fake_llm_generation,
        ):
            result = run_software_engineer_graph(
                self.project_path,
                use_llm_tests=True,
            )

        self.assertEqual(
            [
                "scan",
                "review",
                "fix",
                "patch_review",
                "unit_tests",
                "llm_tests",
                "coverage_feedback",
                "finish",
            ],
            result.node_trace,
        )
        self.assertEqual(3, result.generated_llm_test_count)
        self.assertTrue(result.state["llm_tests"].security_check.passed)

    def test_graph_report_does_not_include_api_key_value(self) -> None:
        with patch(
            "src.workflow.software_engineer_graph.generate_llm_pytest_tests",
            side_effect=_fake_llm_generation,
        ):
            result = run_software_engineer_graph(
                self.project_path,
                use_llm_tests=True,
            )
        data = software_engineer_graph_result_to_dict(result)
        serialized = json.dumps(data)

        self.assertIn("summary", data)
        self.assertIn("llm_tests", data)
        self.assertIn("patch_review", data)
        self.assertIn("coverage_feedback", data)
        self.assertNotIn("unit-test-secret", serialized)

    def test_runs_sandbox_validation_node_with_local_executor(self) -> None:
        result = run_software_engineer_graph(
            self.project_path,
            run_sandbox=True,
            sandbox_executor="local",
        )

        self.assertIn("sandbox_validate", result.node_trace)
        self.assertIn("repair_loop", result.node_trace)
        self.assertTrue(result.state["sandbox_validation"].passed)
        self.assertEqual("complete", result.state["repair_loop"].status)


if __name__ == "__main__":
    unittest.main()
