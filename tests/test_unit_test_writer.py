import shutil
import tempfile
import unittest
from pathlib import Path

from src.agents.unit_test_writer import generate_missing_unit_tests
from src.tools.repo_scanner import scan_repository
from src.tools.unit_test_writer import unit_test_report_to_dict


class UnitTestWriterAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name) / "review_target"
        shutil.copytree("examples/review_target", self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generates_missing_unit_tests_without_applying(self) -> None:
        scan = scan_repository(self.project_path)
        report = generate_missing_unit_tests(self.project_path, scan, apply_changes=False)
        target_file = self.project_path / "tests" / "test_software_engineer_generated.py"

        self.assertFalse(report.applied)
        self.assertFalse(target_file.exists())
        self.assertEqual(4, report.generated_test_count)
        self.assertTrue(report.security_check.passed)
        self.assertEqual(
            [
                "risky_module.divide",
                "risky_module.parse_expression",
                "risky_module.require_api_token",
                "risky_module.hide_error",
            ],
            report.suite.covered_functions,
        )
        self.assertIn("with pytest.raises(ZeroDivisionError):", report.suite.content)
        self.assertIn("assert callable(risky_module.parse_expression)", report.suite.content)

    def test_applies_generated_unit_tests(self) -> None:
        scan = scan_repository(self.project_path)
        report = generate_missing_unit_tests(self.project_path, scan, apply_changes=True)
        target_file = self.project_path / report.test_file_path

        self.assertTrue(report.applied)
        self.assertTrue(target_file.exists())
        self.assertEqual(report.suite.content, target_file.read_text(encoding="utf-8"))

    def test_unit_test_report_dict_contains_summary(self) -> None:
        scan = scan_repository(self.project_path)
        report = generate_missing_unit_tests(self.project_path, scan, apply_changes=False)
        data = unit_test_report_to_dict(report)

        self.assertIn("summary", data)
        self.assertEqual(report.generated_test_count, data["summary"]["generated_test_count"])
        self.assertTrue(data["summary"]["security_check_passed"])


if __name__ == "__main__":
    unittest.main()
