from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.security_checker import SecurityCheckResult, check_generated_test_code
from src.agents.test_generator import GeneratedTestSuite
from src.agents.test_planner import TestPlan, plan_tests
from src.llm.client import LLMClient, OpenAICompatibleLLMClient
from src.llm.config import LLMConfig
from src.llm.prompt_builder import LLMTestPrompt, build_test_generation_prompt
from src.tools.repo_scanner import RepositoryScanResult


@dataclass(frozen=True)
class LLMTestGenerationReport:
    project_path: str
    status: str
    applied: bool
    provider: str
    model: str
    api_key_set: bool
    api_key_env: str
    test_file_path: str
    prompt: LLMTestPrompt
    test_plan: TestPlan
    suite: GeneratedTestSuite | None
    security_check: SecurityCheckResult | None

    @property
    def generated_test_count(self) -> int:
        if self.suite is None:
            return 0
        return self.suite.test_count


def generate_llm_pytest_tests(
    project_path: str | Path,
    scan: RepositoryScanResult,
    apply_changes: bool = False,
    test_file_path: str | Path = "tests/test_software_engineer_llm_generated.py",
    max_functions: int = 8,
    client: LLMClient | None = None,
    config: LLMConfig | None = None,
) -> LLMTestGenerationReport:
    root = Path(project_path).resolve()
    active_config = config or LLMConfig.from_env()
    test_plan = plan_tests(root, scan, max_functions=max_functions)
    prompt = build_test_generation_prompt(root, test_plan)
    target_file = _resolve_project_file(root, test_file_path)

    if client is None and not active_config.api_key_set and active_config.provider != "ollama":
        return LLMTestGenerationReport(
            project_path=str(root),
            status="skipped_missing_api_key",
            applied=False,
            provider=active_config.provider,
            model=active_config.model,
            api_key_set=False,
            api_key_env=active_config.api_key_env,
            test_file_path=target_file.relative_to(root).as_posix(),
            prompt=prompt,
            test_plan=test_plan,
            suite=None,
            security_check=None,
        )

    active_client = client or OpenAICompatibleLLMClient(active_config)
    raw_content = active_client.generate(prompt)
    test_content = _extract_python_code(raw_content)
    security_check = check_generated_test_code(test_content)
    if not security_check.passed:
        return LLMTestGenerationReport(
            project_path=str(root),
            status="security_failed",
            applied=False,
            provider=active_config.provider,
            model=active_config.model,
            api_key_set=active_config.api_key_set,
            api_key_env=active_config.api_key_env,
            test_file_path=target_file.relative_to(root).as_posix(),
            prompt=prompt,
            test_plan=test_plan,
            suite=GeneratedTestSuite(
                test_file_name=target_file.name,
                content=test_content,
                covered_functions=prompt.covered_functions,
            ),
            security_check=security_check,
        )

    if apply_changes:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(test_content, encoding="utf-8")

    return LLMTestGenerationReport(
        project_path=str(root),
        status="generated",
        applied=apply_changes,
        provider=active_config.provider,
        model=active_config.model,
        api_key_set=active_config.api_key_set,
        api_key_env=active_config.api_key_env,
        test_file_path=target_file.relative_to(root).as_posix(),
        prompt=prompt,
        test_plan=test_plan,
        suite=GeneratedTestSuite(
            test_file_name=target_file.name,
            content=test_content,
            covered_functions=prompt.covered_functions,
        ),
        security_check=security_check,
    )


def format_llm_test_generation_report(report: LLMTestGenerationReport) -> str:
    lines = [
        "[Software Engineer Agent LLM Test Generator]",
        "",
        f"Project: {report.project_path}",
        f"Status: {report.status}",
        f"Provider: {report.provider}",
        f"Model: {report.model}",
        f"API Key Env: {report.api_key_env}",
        f"API Key Set: {report.api_key_set}",
        f"Applied: {report.applied}",
        f"Test File: {report.test_file_path}",
        f"Generated Test Cases: {report.generated_test_count}",
        f"Security Check: {_security_check_status(report.security_check)}",
    ]
    return "\n".join(lines)


def _extract_python_code(content: str) -> str:
    match = re.search(r"```(?:python|py)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    extracted = match.group(1) if match else content
    return extracted.strip() + "\n"


def _resolve_project_file(root: Path, test_file_path: str | Path) -> Path:
    candidate = Path(test_file_path)
    target = candidate if candidate.is_absolute() else root / candidate
    resolved = target.resolve()
    if not _is_relative_to(resolved, root):
        raise ValueError("Test file path must stay inside the target project.")
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _security_check_status(result: SecurityCheckResult | None) -> str:
    if result is None:
        return "not_run"
    if result.passed:
        return "passed"
    return f"failed ({result.violation_count} violation(s))"
