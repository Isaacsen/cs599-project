import shutil
import tempfile
import unittest
from pathlib import Path

from src.agents.coverage_feedback import build_coverage_feedback
from src.agents.code_reviewer import ReviewFinding
from src.agents.failure_diagnoser import FailureDiagnosis
from src.agents.llm_code_fixer import fix_code_with_llm
from src.agents.llm_code_reviewer import LLMCodeReviewReport
from src.agents.llm_code_reviewer import review_repository_with_llm
from src.agents.llm_fix_planner import plan_llm_fixes
from src.agents.repair_loop import plan_repair_iteration
from src.agents.result_analyzer import PytestSummary
from src.agents.sandbox_validator import SandboxValidationReport
from src.agents.sandbox_validator import validate_generated_tests_in_sandbox
from src.agents.test_generator import GeneratedTestSuite
from src.agents.unit_test_writer import UnitTestReport, generate_missing_unit_tests
from src.llm.config import LLMConfig
from src.sandbox.local_executor import TestExecutionResult
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


class FakeFixPlannerClient:
    def generate(self, prompt) -> str:
        return '{"target_indexes":[1],"rationale":"Fix the API token handling first."}'


class FakeDangerousFixClient:
    def generate(self, prompt) -> str:
        return """
        {
          "fixes": [
            {
              "file_path": "calculator.py",
              "summary": "Dangerous replacement",
              "replacement_content": "import subprocess\\n\\ndef add(a, b):\\n    subprocess.run(['echo', 'x'])\\n    return a + b\\n\\ndef divide(a, b):\\n    return a / b\\n"
            }
          ]
        }
        """


class FakeInvalidFixPlannerClient:
    def generate(self, prompt) -> str:
        return '{"target_indexes":[999],"rationale":"invalid"}'


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

    def test_llm_fix_planner_uses_llm_selected_order(self) -> None:
        review = LLMCodeReviewReport(
            project_path=str(self.project_path),
            status="reviewed",
            provider="dashscope",
            model="glm-5.2",
            api_key_set=True,
            api_key_env="DASHSCOPE_API_KEY",
            findings=[
                ReviewFinding("calculator.py", 1, "medium", "llm_review", "First issue", "Fix first."),
                ReviewFinding("calculator.py", 2, "low", "llm_review", "Second issue", "Fix second."),
            ],
        )

        plan = plan_llm_fixes(
            review,
            max_targets=1,
            client=FakeFixPlannerClient(),
            config=LLMConfig(
                provider="dashscope",
                model="glm-5.2",
                api_key_set=True,
                api_key_env="DASHSCOPE_API_KEY",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )

        self.assertEqual("llm", plan.planner)
        self.assertEqual([1], [target.finding_index for target in plan.targets])
        self.assertEqual(1, plan.remaining_count)

    def test_llm_code_fixer_blocks_dangerous_patch(self) -> None:
        report = fix_code_with_llm(
            self.project_path,
            self.scan,
            apply_changes=True,
            client=FakeDangerousFixClient(),
            config=LLMConfig(
                provider="dashscope",
                model="glm-5.2",
                api_key_set=True,
                api_key_env="DASHSCOPE_API_KEY",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )

        self.assertEqual("patch_review_failed", report.status)
        self.assertIsNotNone(report.patch_review)
        self.assertFalse(report.patch_review.passed)
        self.assertFalse(report.fixes[0].applied)

    def test_llm_fix_planner_reports_rule_fallback_reason(self) -> None:
        review = LLMCodeReviewReport(
            project_path=str(self.project_path),
            status="reviewed",
            provider="dashscope",
            model="glm-5.2",
            api_key_set=True,
            api_key_env="DASHSCOPE_API_KEY",
            findings=[
                ReviewFinding("calculator.py", 1, "medium", "llm_review", "First issue", "Fix first."),
            ],
        )

        plan = plan_llm_fixes(
            review,
            client=FakeInvalidFixPlannerClient(),
            config=LLMConfig(
                provider="dashscope",
                model="glm-5.2",
                api_key_set=True,
                api_key_env="DASHSCOPE_API_KEY",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )

        self.assertEqual("rule", plan.planner)
        self.assertIn("no valid target indexes", plan.fallback_reason)

    def test_sandbox_validator_runs_generated_tests_locally(self) -> None:
        unit_report = generate_missing_unit_tests(self.project_path, self.scan)
        report = validate_generated_tests_in_sandbox(
            self.project_path,
            unit_tests=unit_report,
            executor="local",
        )

        self.assertTrue(report.passed)
        self.assertEqual(4, report.analysis.total)
        self.assertIn("tests/test_software_engineer_generated.py", report.generated_test_files)

    def test_sandbox_validator_returns_structured_failure_on_executor_error(self) -> None:
        report = validate_generated_tests_in_sandbox(
            self.project_path,
            executor="unsupported",
        )

        self.assertEqual("failed", report.status)
        self.assertEqual(["sandbox_error"], report.diagnosis.failure_types)
        self.assertIn("Unsupported sandbox executor", report.execution.stderr)

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
        report = plan_repair_iteration(sandbox_validation=None, current_iteration=0, max_iterations=1)

        self.assertEqual("planned", report.status)
        self.assertEqual("sandbox_validate", report.next_step)

    def test_repair_loop_routes_import_errors_to_test_generation(self) -> None:
        failed_report = SandboxValidationReport(
            project_path=str(self.project_path),
            status="failed",
            executor="local",
            generated_test_files=["tests/test_generated.py"],
            execution=TestExecutionResult(
                passed=False,
                exit_code=1,
                stdout="ERROR tests/test_generated.py - ModuleNotFoundError",
                stderr="",
                duration_seconds=0.1,
                timed_out=False,
                executor="local",
            ),
            analysis=PytestSummary(passed=0, failed=0, errors=1, total=1, conclusion="failed"),
            diagnosis=FailureDiagnosis(
                status="needs_attention",
                failure_types=["import_error", "pytest_error"],
                key_findings=["tests/test_generated.py"],
                suggestions=["Check generated test imports."],
            ),
            security_checks=[],
        )

        report = plan_repair_iteration(failed_report, current_iteration=0, max_iterations=1)

        self.assertEqual("planned", report.status)
        self.assertEqual("llm_tests", report.next_step)


if __name__ == "__main__":
    unittest.main()
