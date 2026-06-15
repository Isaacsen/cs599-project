import unittest

from src.agents.test_planner import plan_tests
from src.tools.repo_scanner import scan_repository


class TestPlannerAgentTest(unittest.TestCase):
    def test_plans_scenarios_for_sample_project(self) -> None:
        scan = scan_repository("examples/sample_python_project")
        plan = plan_tests("examples/sample_python_project", scan)

        self.assertEqual(2, plan.item_count)
        self.assertEqual(["calculator.add", "calculator.divide"], plan.covered_functions)
        scenarios = [item.scenario for item in plan.items]
        self.assertIn("numeric addition happy path", scenarios)
        self.assertIn("division happy path and zero-division boundary", scenarios)


if __name__ == "__main__":
    unittest.main()
