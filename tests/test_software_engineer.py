import shutil
import tempfile
import unittest
from pathlib import Path

from src.agents.software_engineer import run_software_engineer_agent
from src.tools.software_engineer_writer import software_engineer_report_to_dict


class SoftwareEngineerAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name) / "review_target"
        shutil.copytree("examples/review_target", self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_runs_review_fix_and_unit_test_generation_as_dry_run(self) -> None:
        source_file = self.project_path / "risky_module.py"
        original_content = source_file.read_text(encoding="utf-8")

        report = run_software_engineer_agent(self.project_path)

        self.assertEqual(7, report.finding_count)
        self.assertEqual(6, report.fix_edit_count)
        self.assertEqual(3, report.generated_test_count)
        self.assertFalse(report.fix_plan.applied)
        self.assertFalse(report.unit_tests.applied)
        self.assertEqual(original_content, source_file.read_text(encoding="utf-8"))
        self.assertFalse((self.project_path / "tests" / "test_software_engineer_generated.py").exists())

    def test_report_dict_contains_combined_summary(self) -> None:
        report = run_software_engineer_agent(self.project_path)
        data = software_engineer_report_to_dict(report)

        self.assertEqual(7, data["summary"]["finding_count"])
        self.assertEqual(6, data["summary"]["fix_edit_count"])
        self.assertEqual(3, data["summary"]["generated_test_count"])
        self.assertIn("review", data)
        self.assertIn("fix_plan", data)
        self.assertIn("unit_tests", data)


if __name__ == "__main__":
    unittest.main()
