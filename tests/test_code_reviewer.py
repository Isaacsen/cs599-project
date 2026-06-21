import unittest

from src.agents.code_reviewer import review_repository
from src.tools.repo_scanner import scan_repository
from src.tools.review_writer import review_report_to_dict


class CodeReviewerAgentTest(unittest.TestCase):
    def test_reviews_example_project_for_missing_coverage(self) -> None:
        scan = scan_repository("examples/review_target")
        report = review_repository("examples/review_target", scan)
        rules = {finding.rule for finding in report.findings}

        self.assertIn("missing_test", rules)
        self.assertEqual(3, report.finding_count)
        self.assertEqual(0, report.high_count)

    def test_review_report_dict_contains_summary(self) -> None:
        scan = scan_repository("examples/review_target")
        report = review_repository("examples/review_target", scan)
        data = review_report_to_dict(report)

        self.assertIn("summary", data)
        self.assertEqual(report.finding_count, data["summary"]["finding_count"])
        self.assertTrue(data["findings"])


if __name__ == "__main__":
    unittest.main()
