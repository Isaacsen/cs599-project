import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.code_reviewer import ReviewFinding
from src.agents.failure_diagnoser import FailureDiagnosis
from src.agents.llm_code_fixer import LLMCodeFix, LLMCodeFixReport
from src.agents.llm_code_reviewer import LLMCodeReviewReport
from src.agents.llm_test_generator import LLMTestGenerationReport
from src.agents.result_analyzer import PytestSummary
from src.agents.sandbox_validator import SandboxValidationReport
from src.agents.security_checker import check_generated_test_code
from src.agents.test_generator import GeneratedTestSuite
from src.agents.test_planner import plan_tests
from src.sandbox.local_executor import TestExecutionResult
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


def _fake_llm_review(project_path, scan):
    root = Path(project_path).resolve()
    return LLMCodeReviewReport(
        project_path=str(root),
        status="reviewed",
        provider="dashscope",
        model="glm-5.2",
        api_key_set=True,
        api_key_env="DASHSCOPE_API_KEY",
        findings=[
            ReviewFinding(
                file_path="risky_module.py",
                line=4,
                severity="medium",
                rule="llm_review",
                message="Function should keep explicit division-by-zero behavior covered by tests.",
                suggestion="Generate pytest coverage for normal and zero-denominator cases.",
            )
        ],
        raw_response='{"findings":[]}',
    )


def _fake_llm_fix(project_path, scan, llm_review=None, sandbox_validation=None, repair_actions=None, apply_changes=False):
    root = Path(project_path).resolve()
    return LLMCodeFixReport(
        project_path=str(root),
        status="planned",
        applied=apply_changes,
        provider="dashscope",
        model="glm-5.2",
        api_key_set=True,
        api_key_env="DASHSCOPE_API_KEY",
        fixes=[
            LLMCodeFix(
                file_path="risky_module.py",
                summary="Keep division behavior explicit and document parser constraints.",
                replacement_content=(root / "risky_module.py").read_text(encoding="utf-8"),
                applied=False,
            )
        ],
        raw_response='{"fixes":[]}',
    )


def _sandbox_report(project_path, passed, failure_types=None, suggestions=None):
    active_failure_types = failure_types or ["assertion_failure", "pytest_failure"]
    analysis = PytestSummary(
        passed=1 if passed else 0,
        failed=0 if passed else 1,
        total=1,
        conclusion="passed" if passed else "failed",
    )
    execution = TestExecutionResult(
        passed=passed,
        exit_code=0 if passed else 1,
        stdout="============================= 1 passed in 0.01s ============================="
        if passed
        else "FAILED tests/test_generated.py::test_generated\n=========================== 1 failed in 0.01s ===========================",
        stderr="",
        duration_seconds=0.01,
        timed_out=False,
        executor="local",
    )
    diagnosis = FailureDiagnosis(
        status="no_issue" if passed else "needs_attention",
        failure_types=[] if passed else active_failure_types,
        key_findings=[] if passed else ["tests/test_generated.py::test_generated"],
        suggestions=["All tests passed. Keep generated tests as regression coverage."]
        if passed
        else suggestions
        or ["Compare expected behavior with implementation; update code or adjust an invalid generated expectation."],
    )
    return SandboxValidationReport(
        project_path=str(Path(project_path).resolve()),
        status="passed" if passed else "failed",
        executor="local",
        generated_test_files=["tests/test_software_engineer_llm_generated.py"],
        execution=execution,
        analysis=analysis,
        diagnosis=diagnosis,
        security_checks=[],
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

        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix),
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation),
        ):
            result = run_software_engineer_graph(self.project_path)

        self.assertEqual("completed", result.state["status"])
        self.assertIn(result.graph_runtime, {"langgraph", "fallback"})
        self.assertEqual(
            ["scan", "llm_review", "llm_fix", "llm_tests", "coverage_feedback", "finish"],
            result.node_trace,
        )
        self.assertEqual(1, result.state["llm_review"].finding_count)
        self.assertEqual(1, result.state["llm_fix"].fix_count)
        self.assertEqual(3, result.generated_llm_test_count)
        self.assertEqual(original_content, source_file.read_text(encoding="utf-8"))
        self.assertFalse((self.project_path / "tests" / "test_software_engineer_llm_generated.py").exists())

    def test_runs_llm_branch_with_injected_generation(self) -> None:
        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix),
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation),
        ):
            result = run_software_engineer_graph(
                self.project_path,
            )

        self.assertEqual(
            [
                "scan",
                "llm_review",
                "llm_fix",
                "llm_tests",
                "coverage_feedback",
                "finish",
            ],
            result.node_trace,
        )
        self.assertEqual(3, result.generated_llm_test_count)
        self.assertTrue(result.state["llm_tests"].security_check.passed)

    def test_graph_report_does_not_include_api_key_value(self) -> None:
        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix),
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation),
        ):
            result = run_software_engineer_graph(
                self.project_path,
            )
        data = software_engineer_graph_result_to_dict(result)
        serialized = json.dumps(data)

        self.assertIn("summary", data)
        self.assertNotIn("review", data)
        self.assertNotIn("unit_tests", data)
        self.assertIn("llm_fix", data)
        self.assertIn("llm_tests", data)
        self.assertNotIn("fix_plan", data)
        self.assertNotIn("patch_review", data)
        self.assertIn("coverage_feedback", data)
        self.assertNotIn("unit-test-secret", serialized)

    def test_runs_sandbox_validation_node_with_local_executor(self) -> None:
        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix),
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation),
        ):
            result = run_software_engineer_graph(
                self.project_path,
                run_sandbox=True,
                sandbox_executor="local",
            )

        self.assertIn("sandbox_validate", result.node_trace)
        self.assertIn("repair_loop", result.node_trace)
        self.assertTrue(result.state["sandbox_validation"].passed)
        self.assertEqual("complete", result.state["repair_loop"].status)

    def test_repair_loop_retries_llm_tests_after_sandbox_failure(self) -> None:
        sandbox_reports = [
            _sandbox_report(self.project_path, passed=False),
            _sandbox_report(self.project_path, passed=True),
        ]

        def fake_sandbox_validation(*args, **kwargs):
            return sandbox_reports.pop(0)

        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix) as fix_mock,
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation) as generate_mock,
            patch(
                "src.workflow.software_engineer_graph.validate_generated_tests_in_sandbox",
                side_effect=fake_sandbox_validation,
            ) as sandbox_mock,
        ):
            result = run_software_engineer_graph(
                self.project_path,
                run_sandbox=True,
                sandbox_executor="local",
                repair_iterations=1,
            )

        self.assertEqual(
            [
                "scan",
                "llm_review",
                "llm_fix",
                "llm_tests",
                "sandbox_validate",
                "repair_loop",
                "llm_fix",
                "llm_tests",
                "sandbox_validate",
                "repair_loop",
                "coverage_feedback",
                "finish",
            ],
            result.node_trace,
        )
        self.assertEqual(2, fix_mock.call_count)
        self.assertEqual(2, generate_mock.call_count)
        self.assertEqual(2, sandbox_mock.call_count)
        self.assertEqual(2, len(result.state["repair_history"]))
        self.assertEqual("llm_fix", result.state["repair_history"][0].next_step)
        self.assertEqual("complete", result.state["repair_loop"].status)

    def test_repair_loop_routes_generated_test_errors_to_llm_tests(self) -> None:
        sandbox_reports = [
            _sandbox_report(
                self.project_path,
                passed=False,
                failure_types=["import_error", "pytest_error"],
                suggestions=["Check generated test imports."],
            ),
            _sandbox_report(self.project_path, passed=True),
        ]

        def fake_sandbox_validation(*args, **kwargs):
            return sandbox_reports.pop(0)

        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix) as fix_mock,
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation) as generate_mock,
            patch(
                "src.workflow.software_engineer_graph.validate_generated_tests_in_sandbox",
                side_effect=fake_sandbox_validation,
            ) as sandbox_mock,
        ):
            result = run_software_engineer_graph(
                self.project_path,
                run_sandbox=True,
                sandbox_executor="local",
                repair_iterations=1,
            )

        self.assertEqual(
            [
                "scan",
                "llm_review",
                "llm_fix",
                "llm_tests",
                "sandbox_validate",
                "repair_loop",
                "llm_tests",
                "sandbox_validate",
                "repair_loop",
                "coverage_feedback",
                "finish",
            ],
            result.node_trace,
        )
        self.assertEqual(1, fix_mock.call_count)
        self.assertEqual(2, generate_mock.call_count)
        self.assertEqual(2, sandbox_mock.call_count)
        self.assertEqual("llm_tests", result.state["repair_history"][0].next_step)

    def test_repair_loop_stops_after_three_retries(self) -> None:
        sandbox_reports = [_sandbox_report(self.project_path, passed=False) for _ in range(4)]

        def fake_sandbox_validation(*args, **kwargs):
            return sandbox_reports.pop(0)

        with (
            patch("src.workflow.software_engineer_graph.review_repository_with_llm", side_effect=_fake_llm_review),
            patch("src.workflow.software_engineer_graph.fix_code_with_llm", side_effect=_fake_llm_fix) as fix_mock,
            patch("src.workflow.software_engineer_graph.generate_llm_pytest_tests", side_effect=_fake_llm_generation) as generate_mock,
            patch(
                "src.workflow.software_engineer_graph.validate_generated_tests_in_sandbox",
                side_effect=fake_sandbox_validation,
            ) as sandbox_mock,
        ):
            result = run_software_engineer_graph(
                self.project_path,
                run_sandbox=True,
                sandbox_executor="local",
                repair_iterations=3,
            )

        self.assertEqual(4, fix_mock.call_count)
        self.assertEqual(4, generate_mock.call_count)
        self.assertEqual(4, sandbox_mock.call_count)
        self.assertEqual(4, len(result.state["repair_history"]))
        self.assertEqual("blocked", result.state["repair_loop"].status)
        self.assertEqual("manual_review", result.state["repair_loop"].next_step)
        self.assertEqual(3, result.state["repair_loop"].iteration)


if __name__ == "__main__":
    unittest.main()
