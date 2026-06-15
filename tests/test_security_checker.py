import unittest

from src.agents.security_checker import check_generated_test_code


class SecurityCheckerTest(unittest.TestCase):
    def test_allows_safe_pytest_code(self) -> None:
        result = check_generated_test_code("def test_sample():\n    assert 1 + 1 == 2\n")

        self.assertTrue(result.passed)
        self.assertEqual(0, result.violation_count)

    def test_rejects_forbidden_import(self) -> None:
        result = check_generated_test_code("import subprocess\n")

        self.assertFalse(result.passed)
        self.assertEqual("forbidden_import", result.violations[0].rule)
        self.assertEqual("subprocess", result.violations[0].detail)

    def test_rejects_forbidden_call(self) -> None:
        result = check_generated_test_code("def test_sample():\n    eval('1 + 1')\n")

        self.assertFalse(result.passed)
        self.assertEqual("forbidden_call", result.violations[0].rule)
        self.assertEqual("eval", result.violations[0].detail)


if __name__ == "__main__":
    unittest.main()
