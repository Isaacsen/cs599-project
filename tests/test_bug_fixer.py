import shutil
import tempfile
import unittest
from pathlib import Path

from src.agents.bug_fixer import fix_repository
from src.agents.code_reviewer import review_repository
from src.tools.fix_writer import fix_plan_to_dict
from src.tools.repo_scanner import scan_repository


class BugFixerAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name) / "review_target"
        shutil.copytree("examples/review_target", self.project_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_plans_safe_fixes_without_applying(self) -> None:
        target_file = self.project_path / "risky_module.py"
        original_content = target_file.read_text(encoding="utf-8")
        scan = scan_repository(self.project_path)

        plan = fix_repository(self.project_path, scan, apply_changes=False)
        rules = {edit.rule for edit in plan.edits}

        self.assertFalse(plan.applied)
        self.assertEqual(original_content, target_file.read_text(encoding="utf-8"))
        self.assertIn("dangerous_eval_fix", rules)
        self.assertIn("hardcoded_secret_fix", rules)
        self.assertIn("broad_exception_fix", rules)
        self.assertIn("division_guard_fix", rules)
        self.assertGreaterEqual(plan.edit_count, 4)

    def test_applies_safe_fixes(self) -> None:
        scan = scan_repository(self.project_path)
        plan = fix_repository(self.project_path, scan, apply_changes=True)
        target_file = self.project_path / "risky_module.py"
        content = target_file.read_text(encoding="utf-8")

        self.assertTrue(plan.applied)
        self.assertIn("import ast", content)
        self.assertIn("import os", content)
        self.assertIn("ast.literal_eval(expression)", content)
        self.assertIn('API_TOKEN = os.getenv("API_TOKEN", "")', content)
        self.assertIn("except ValueError:", content)
        self.assertIn('raise ZeroDivisionError("division by zero")', content)

        fixed_scan = scan_repository(self.project_path)
        review = review_repository(self.project_path, fixed_scan)
        remaining_rules = {finding.rule for finding in review.findings}

        self.assertNotIn("dangerous_call", remaining_rules)
        self.assertNotIn("hardcoded_secret", remaining_rules)
        self.assertNotIn("broad_exception", remaining_rules)
        self.assertNotIn("division_risk", remaining_rules)

    def test_fix_plan_dict_contains_summary(self) -> None:
        scan = scan_repository(self.project_path)
        plan = fix_repository(self.project_path, scan, apply_changes=False)
        data = fix_plan_to_dict(plan)

        self.assertIn("summary", data)
        self.assertEqual(plan.edit_count, data["summary"]["edit_count"])
        self.assertTrue(data["edits"])


if __name__ == "__main__":
    unittest.main()
