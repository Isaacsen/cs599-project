import unittest

from src.agents.failure_diagnoser import diagnose_failure
from src.agents.result_analyzer import analyze_pytest_result
from src.sandbox.local_executor import TestExecutionResult


class FailureDiagnoserTest(unittest.TestCase):
    def test_no_issue_when_tests_pass(self) -> None:
        execution = TestExecutionResult(
            passed=True,
            exit_code=0,
            stdout="============================== 2 passed in 0.01s ==============================\n",
            stderr="",
            duration_seconds=0.1,
            timed_out=False,
        )

        diagnosis = diagnose_failure(execution, analyze_pytest_result(execution))

        self.assertEqual("no_issue", diagnosis.status)
        self.assertEqual([], diagnosis.failure_types)
        self.assertIn("All tests passed", diagnosis.suggestions[0])

    def test_classifies_assertion_failure(self) -> None:
        execution = TestExecutionResult(
            passed=False,
            exit_code=1,
            stdout=(
                "FAILED tests/test_math.py::test_add - AssertionError\n"
                "================== 1 failed, 1 passed in 0.12s ==================\n"
            ),
            stderr="",
            duration_seconds=0.2,
            timed_out=False,
        )

        diagnosis = diagnose_failure(execution, analyze_pytest_result(execution))

        self.assertEqual("needs_attention", diagnosis.status)
        self.assertIn("assertion_failure", diagnosis.failure_types)
        self.assertIn("pytest_failure", diagnosis.failure_types)
        self.assertEqual(["tests/test_math.py::test_add"], diagnosis.key_findings)

    def test_classifies_timeout(self) -> None:
        execution = TestExecutionResult(
            passed=False,
            exit_code=None,
            stdout="",
            stderr="pytest timed out after 1 seconds",
            duration_seconds=1.0,
            timed_out=True,
        )

        diagnosis = diagnose_failure(execution, analyze_pytest_result(execution))

        self.assertIn("timeout", diagnosis.failure_types)
        self.assertTrue(any("loops" in suggestion for suggestion in diagnosis.suggestions))


if __name__ == "__main__":
    unittest.main()
