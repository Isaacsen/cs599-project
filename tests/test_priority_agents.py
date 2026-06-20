import shutil
import tempfile
import unittest
from pathlib import Path

from src.agents.bug_fixer import FixEdit, FixPlan
from src.agents.coverage_feedback import build_coverage_feedback
from src.agents.llm_code_reviewer import review_repository_with_llm
from src.agents.patch_reviewer import review_fix_plan
from src.agents.repair_loop import plan_repair_iteration
from src.agents.sandbox_validator import validate_generated_tests_in_sandbox
from src.agents.test_generator import GeneratedTestSuite
from src.agents.unit_test_writer import UnitTestReport, generate_missing_unit_tests
from src.llm.config import LLMConfig
from src.tools.repo_scanner import scan_repository


class FakeReviewClient:
    def generate(self, prompt) -> str:
        return """
        {
          "findings": [
            {
              "file_path": "calculator.py",
              "line": 5,
              "severity": "medium",
              "rule": "llm_boundary_review",
              "message": "Division should document zero denominator behavior.",
              "suggestion": "Keep an explicit zero-division regression test."
            }
          ]
        }
        """


class PriorityAgentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name) / "sample_python_project"
        shutil.copytree("examples/sample_python_project", self.project_path)
        self.scan = scan_repository(self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_llm_code_reviewer_parses_structured_findings(self) -> None:
        report = review_repository_with_llm(
            self.project_path,
            self.scan,
            client=FakeReviewClient(),
            config=LLMConfig(
                provider="dashscope",
                model="glm-5.2",
                api_key_set=True,
                api_key_env="DASHSCOPE_API_KEY",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )

        self.assertEqual("reviewed", report.status)
        self.assertEqual(1, report.finding_count)
        self.assertEqual("llm_boundary_review", report.findings[0].rule)

    def test_patch_reviewer_flags_dangerous_patch_content(self) -> None:
        plan = FixPlan(
            project_path=str(self.project_path),
            applied=False,
            edits=[
                FixEdit(
                    file_path="calculator.py",
                    line=1,
                    rule="dangerous_eval_fix",
                    description="bad edit",
                    before="x = 1",
                    after="subprocess.run(['cmd'])",
                )
            ],
        )
        report = review_fix_plan(self.project_path, self.scan, plan)

        self.assertFalse(report.passed)
        self.assertEqual("dangerous_patch_content", report.findings[0].rule)

    def test_sandbox_validator_runs_generated_tests_locally(self) -> None:
        unit_report = generate_missing_unit_tests(self.project_path, self.scan)
        report = validate_generated_tests_in_sandbox(
            self.project_path,
            unit_tests=unit_report,
            executor="local",
        )

        self.assertTrue(report.passed)
        self.assertEqual(4, report.analysis.total)
        self.assertIn("tests/test_testguard_generated.py", report.generated_test_files)

    def test_coverage_feedback_reports_missing_functions(self) -> None:
        unit_report = UnitTestReport(
            project_path=str(self.project_path),
            applied=False,
            test_file_path="tests/test_partial.py",
            test_plan=generate_missing_unit_tests(self.project_path, self.scan).test_plan,
            suite=GeneratedTestSuite(
                test_file_name="test_partial.py",
                content="def test_add():\n    assert True\n",
                covered_functions=["calculator.add"],
            ),
            security_check=generate_missing_unit_tests(self.project_path, self.scan).security_check,
        )
        report = build_coverage_feedback(self.project_path, self.scan, unit_tests=unit_report)

        self.assertLess(report.coverage_ratio, 1.0)
        self.assertIn("calculator.divide", report.missing_functions)

    def test_repair_loop_plans_next_step_after_failure(self) -> None:
        report = plan_repair_iteration(patch_review=None, sandbox_validation=None, max_iterations=1)

        self.assertEqual("planned", report.status)
        self.assertEqual("test_plan", report.next_step)


if __name__ == "__main__":
    unittest.main()
