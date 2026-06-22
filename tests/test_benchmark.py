import unittest

from src.agents.failure_diagnoser import FailureDiagnosis
from src.agents.llm_test_generator import LLMTestGenerationReport
from src.agents.result_analyzer import PytestSummary
from src.agents.sandbox_validator import SandboxValidationReport
from src.agents.test_planner import TestPlan
from src.evaluation.benchmark import BenchmarkCase, BenchmarkResult, summarize_results
from src.llm.prompt_builder import LLMTestPrompt
from src.sandbox.local_executor import TestExecutionResult
from src.workflow.software_engineer_graph import SoftwareEngineerGraphResult


class BenchmarkSummaryTest(unittest.TestCase):
    def test_summarizes_benchmark_results(self) -> None:
        execution = TestExecutionResult(
            passed=True,
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=1.5,
            timed_out=False,
        )
        report = SoftwareEngineerGraphResult(
            state={
                "project_path": "examples/sample_python_project",
                "status": "completed",
                "node_trace": [],
                "llm_tests": LLMTestGenerationReport(
                    project_path="examples/sample_python_project",
                    status="generated",
                    applied=False,
                    provider="dashscope",
                    model="glm-5.2",
                    api_key_set=True,
                    api_key_env="DASHSCOPE_API_KEY",
                    test_file_path="tests/test_generated.py",
                    prompt=LLMTestPrompt(system="", user="", covered_functions=[]),
                    test_plan=TestPlan(items=[]),
                    suite=None,
                    security_check=None,
                ),
                "sandbox_validation": SandboxValidationReport(
                    project_path="examples/sample_python_project",
                    status="passed",
                    executor="local",
                    generated_test_files=[],
                    execution=execution,
                    analysis=PytestSummary(passed=5, total=5, conclusion="passed"),
                    diagnosis=FailureDiagnosis(
                        status="no_issue",
                        failure_types=[],
                        key_findings=[],
                        suggestions=["All tests passed."],
                    ),
                    security_checks=[],
                ),
            }
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
