import unittest

from src.agents.code_reviewer import review_repository
from src.tools.repo_scanner import scan_repository
from src.tools.review_writer import review_report_to_dict


class CodeReviewerAgentTest(unittest.TestCase):
    def test_reviews_risky_example_project(self) -> None:
        scan = scan_repository("examples/review_target")
        report = review_repository("examples/review_target", scan)
        rules = {finding.rule for finding in report.findings}

        self.assertIn("dangerous_call", rules)
        self.assertIn("division_risk", rules)
        self.assertIn("missing_test", rules)
        self.assertIn("broad_exception", rules)
        self.assertIn("hardcoded_secret", rules)
        self.assertGreaterEqual(report.high_count, 2)

    def test_review_report_dict_contains_summary(self) -> None:
        scan = scan_repository("examples/review_target")
        report = review_repository("examples/review_target", scan)
        data = review_report_to_dict(report)

        self.assertIn("summary", data)
        self.assertEqual(report.finding_count, data["summary"]["finding_count"])
        self.assertTrue(data["findings"])


if __name__ == "__main__":
    unittest.main()
