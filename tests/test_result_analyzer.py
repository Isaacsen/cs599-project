import unittest

from src.agents.failure_diagnoser import diagnose_failure
from src.agents.result_analyzer import analyze_pytest_result
from src.sandbox.local_executor import TestExecutionResult


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

    def test_diagnoses_successful_execution(self) -> None:
        execution = TestExecutionResult(
            passed=True,
            exit_code=0,
            stdout="============================== 2 passed in 0.08s ==============================\n",
            stderr="",
            duration_seconds=0.2,
            timed_out=False,
        )
        analysis = analyze_pytest_result(execution)
        diagnosis = diagnose_failure(execution, analysis)

        self.assertEqual("no_issue", diagnosis.status)
        self.assertEqual([], diagnosis.failure_types)

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
