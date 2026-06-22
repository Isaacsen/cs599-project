import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm.config import LLMConfig, get_llm_api_key, normalize_provider
from src.llm.prompt_builder import build_test_generation_prompt
from src.tools.prompt_writer import write_llm_prompt
from src.tools.repo_scanner import scan_repository
from src.agents.test_planner import plan_tests


class LLMTestPromptBuilderTest(unittest.TestCase):
    def test_builds_prompt_from_test_plan_and_source(self) -> None:
        scan = scan_repository("examples/sample_python_project")
        plan = plan_tests("examples/sample_python_project", scan)

        prompt = build_test_generation_prompt("examples/sample_python_project", plan)

        self.assertIn("生成的测试必须安全", prompt.system)
        self.assertIn("只返回一个 pytest 文件的 Python 代码", prompt.user)
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
                config=LLMConfig(
                    provider="deepseek",
                    model="deepseek-v4-pro",
                    api_key_set=True,
                    api_key_env="DEEPSEEK_API_KEY",
                ),
            )
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(data["llm_config"]["api_key_set"])
        self.assertEqual("DEEPSEEK_API_KEY", data["llm_config"]["api_key_env"])
        self.assertNotIn("LLM_API_KEY", json.dumps(data))
        self.assertNotIn("unit-test-value", json.dumps(data))
        self.assertIn("prompt", data)
        self.assertNotIn("system", data["prompt"])
        self.assertNotIn("user", data["prompt"])
        self.assertIn("user_char_count", data["prompt"])

    def test_dashscope_api_key_is_default_env(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DASHSCOPE_API_KEY": "unit-test-value",
                "LLM_API_KEY": "fallback-value",
            },
            clear=True,
        ):
            api_key, api_key_env = get_llm_api_key()
            config = LLMConfig.from_env()

        self.assertEqual("unit-test-value", api_key)
        self.assertEqual("DASHSCOPE_API_KEY", api_key_env)
        self.assertEqual("dashscope", config.provider)
        self.assertEqual("glm-5.2", config.model)
        self.assertTrue(config.api_key_set)
        self.assertEqual("DASHSCOPE_API_KEY", config.api_key_env)
        self.assertEqual(120, config.timeout_seconds)
        self.assertEqual(1, config.max_retries)

    def test_llm_timeout_and_retries_are_configurable(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DASHSCOPE_API_KEY": "unit-test-value",
                "LLM_TIMEOUT_SECONDS": "180",
                "LLM_MAX_RETRIES": "2",
            },
            clear=True,
        ):
            config = LLMConfig.from_env()

        self.assertEqual(180, config.timeout_seconds)
        self.assertEqual(2, config.max_retries)

    def test_deepseek_api_key_is_supported_when_provider_is_set(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "unit-test-value",
                "LLM_API_KEY": "fallback-value",
            },
            clear=True,
        ):
            api_key, api_key_env = get_llm_api_key()
            config = LLMConfig.from_env()

        self.assertEqual("unit-test-value", api_key)
        self.assertEqual("DEEPSEEK_API_KEY", api_key_env)
        self.assertEqual("deepseek", config.provider)
        self.assertEqual("deepseek-v4-pro", config.model)
        self.assertTrue(config.api_key_set)
        self.assertEqual("DEEPSEEK_API_KEY", config.api_key_env)

    def test_dashscope_api_key_is_supported(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "dashscope",
                "DASHSCOPE_API_KEY": "unit-test-value",
                "LLM_API_KEY": "fallback-value",
            },
            clear=True,
        ):
            api_key, api_key_env = get_llm_api_key()
            config = LLMConfig.from_env()

        self.assertEqual("unit-test-value", api_key)
        self.assertEqual("DASHSCOPE_API_KEY", api_key_env)
        self.assertEqual("dashscope", config.provider)
        self.assertEqual("glm-5.2", config.model)
        self.assertTrue(config.api_key_set)
        self.assertEqual("DASHSCOPE_API_KEY", config.api_key_env)

    def test_dashscope_provider_aliases(self) -> None:
        self.assertEqual("dashscope", normalize_provider("aliyun"))
        self.assertEqual("dashscope", normalize_provider("alibaba"))
        self.assertEqual("dashscope", normalize_provider("qwen"))


if __name__ == "__main__":
    unittest.main()
