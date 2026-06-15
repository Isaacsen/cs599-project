import unittest

from src.evaluation.benchmark import BenchmarkCase, BenchmarkResult, summarize_results
from src.agents.result_analyzer import PytestSummary
from src.sandbox.local_executor import TestExecutionResult
from src.tools.repo_scanner import RepositoryScanResult
from src.workflow.pipeline import PipelineReport


class BenchmarkSummaryTest(unittest.TestCase):
    def test_summarizes_benchmark_results(self) -> None:
        report = PipelineReport(
            scan=RepositoryScanResult(
                project_path="examples/sample_python_project",
                language="Python",
                test_framework="pytest",
                source_files=["calculator.py"],
                test_files=["test_calculator.py"],
            ),
            execution=TestExecutionResult(
                passed=True,
                exit_code=0,
                stdout="",
                stderr="",
                duration_seconds=1.5,
                timed_out=False,
            ),
            analysis=PytestSummary(passed=5, total=5, conclusion="passed"),
        )
        result = BenchmarkResult(
            case=BenchmarkCase(name="sample", project_path="examples/sample_python_project"),
            report=report,
        )

        summary = summarize_results([result])

        self.assertEqual(1, summary.total_cases)
        self.assertEqual(1, summary.passed_cases)
        self.assertEqual(0, summary.failed_cases)
        self.assertEqual(1.0, summary.pass_rate)
        self.assertEqual(5, summary.total_pytest_cases)
        self.assertEqual(1.5, summary.total_duration_seconds)


if __name__ == "__main__":
    unittest.main()
