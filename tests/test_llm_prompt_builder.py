import json
import tempfile
import unittest
from pathlib import Path

from src.llm.config import LLMConfig
from src.llm.prompt_builder import build_test_generation_prompt
from src.tools.prompt_writer import write_llm_prompt
from src.tools.repo_scanner import scan_repository
from src.agents.test_planner import plan_tests


class LLMTestPromptBuilderTest(unittest.TestCase):
    def test_builds_prompt_from_test_plan_and_source(self) -> None:
        scan = scan_repository("examples/sample_python_project")
        plan = plan_tests("examples/sample_python_project", scan)

        prompt = build_test_generation_prompt("examples/sample_python_project", plan)

        self.assertIn("Generate safe pytest tests only", prompt.system)
        self.assertIn("calculator.add", prompt.user)
        self.assertIn("calculator.divide", prompt.user)
        self.assertIn("def add", prompt.user)
        self.assertEqual(["calculator.add", "calculator.divide"], prompt.covered_functions)

    def test_writes_prompt_json_without_secret_value(self) -> None:
        scan = scan_repository("examples/sample_python_project")
        plan = plan_tests("examples/sample_python_project", scan)
        prompt = build_test_generation_prompt("examples/sample_python_project", plan)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_llm_prompt(
                prompt,
                Path(temp_dir) / "prompt.json",
                config=LLMConfig(provider="deepseek", model="deepseek-chat", api_key_set=True),
            )
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(data["llm_config"]["api_key_set"])
        self.assertNotIn("LLM_API_KEY", json.dumps(data))
        self.assertIn("prompt", data)


if __name__ == "__main__":
    unittest.main()
