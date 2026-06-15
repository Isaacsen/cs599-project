import json
import tempfile
import unittest
from pathlib import Path

from src.agents.failure_diagnoser import diagnose_failure
from src.agents.result_analyzer import analyze_pytest_result
from src.agents.security_checker import check_generated_test_code
from src.agents.test_generator import GeneratedTestSuite
from src.agents.test_planner import plan_tests
from src.sandbox.local_executor import TestExecutionResult
from src.tools.repo_scanner import scan_repository
from src.tools.report_writer import write_json_report
from src.workflow.pipeline import PipelineReport


class ResultAnalyzerTest(unittest.TestCase):
    def test_parses_successful_pytest_summary(self) -> None:
        execution = TestExecutionResult(
            passed=True,
            exit_code=0,
            stdout="============================== 5 passed in 0.08s ==============================\n",
            stderr="",
            duration_seconds=0.2,
            timed_out=False,
        )

        summary = analyze_pytest_result(execution)

        self.assertEqual(5, summary.total)
        self.assertEqual(5, summary.passed)
        self.assertEqual(0, summary.failed)
        self.assertEqual("passed", summary.conclusion)

    def test_parses_failed_pytest_summary(self) -> None:
        execution = TestExecutionResult(
            passed=False,
            exit_code=1,
            stdout="================== 1 failed, 2 passed, 1 warning in 0.12s ==================\n",
            stderr="",
            duration_seconds=0.2,
            timed_out=False,
        )

        summary = analyze_pytest_result(execution)

        self.assertEqual(3, summary.total)
        self.assertEqual(2, summary.passed)
        self.assertEqual(1, summary.failed)
        self.assertEqual(1, summary.warnings)
        self.assertEqual("failed", summary.conclusion)

    def test_writes_json_report(self) -> None:
        execution = TestExecutionResult(
            passed=True,
            exit_code=0,
            stdout="============================== 2 passed in 0.08s ==============================\n",
            stderr="",
            duration_seconds=0.2,
            timed_out=False,
        )
        report = PipelineReport(
            scan=scan_repository("examples/sample_python_project"),
            execution=execution,
            analysis=analyze_pytest_result(execution),
            diagnosis=diagnose_failure(execution, analyze_pytest_result(execution)),
            security_check=check_generated_test_code("def test_sample():\n    assert True\n"),
            test_plan=plan_tests(
                "examples/sample_python_project",
                scan_repository("examples/sample_python_project"),
            ),
            generated_suite=GeneratedTestSuite(
                test_file_name="test_testguard_generated.py",
                content="def test_sample():\n    assert True\n",
                covered_functions=["calculator.add", "calculator.divide"],
            ),
            generated_tests_enabled=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = write_json_report(report, Path(temp_dir) / "report.json")
            data = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual("Python", data["scan"]["language"])
        self.assertTrue(data["generated_tests_enabled"])
        self.assertEqual(2, len(data["test_plan"]["items"]))
        self.assertEqual(2, len(data["generated_suite"]["covered_functions"]))
        self.assertIn("analysis", data)
        self.assertEqual("no_issue", data["diagnosis"]["status"])
        self.assertTrue(data["security_check"]["passed"])

    def test_timeout_conclusion(self) -> None:
        execution = TestExecutionResult(
            passed=False,
            exit_code=None,
            stdout="",
            stderr="pytest timed out",
            duration_seconds=30.0,
            timed_out=True,
        )

        summary = analyze_pytest_result(execution)

        self.assertEqual("timeout", summary.conclusion)


if __name__ == "__main__":
    unittest.main()
