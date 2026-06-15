import unittest

from src.agents.test_generator import generate_pytest_tests, validate_generated_test_code
from src.tools.repo_scanner import scan_repository


class TestGeneratorAgentTest(unittest.TestCase):
    def test_generates_pytest_cases_for_sample_project(self) -> None:
        scan = scan_repository("examples/sample_python_project")
        suite = generate_pytest_tests("examples/sample_python_project", scan)

        self.assertEqual("test_testguard_generated.py", suite.test_file_name)
        self.assertIn("import calculator as calculator", suite.content)
        self.assertIn("assert calculator.add(1, 2) == 3", suite.content)
        self.assertIn("assert calculator.divide(4, 2) == 2", suite.content)
        self.assertIn("with pytest.raises(ZeroDivisionError):", suite.content)
        self.assertEqual(
            ["calculator.add", "calculator.divide"],
            suite.covered_functions,
        )

    def test_rejects_forbidden_imports(self) -> None:
        with self.assertRaises(ValueError):
            validate_generated_test_code("import subprocess\n")


if __name__ == "__main__":
    unittest.main()
