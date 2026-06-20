# Project Artifacts

## Specs

- `docs/CS599_大作业报告.md`：最终报告 Markdown 草稿，可转 PDF。
- `docs/specs/product_spec.md`：产品规格，描述问题、用户、功能需求和非功能需求。
- `docs/specs/architecture_spec.md`：架构规格，描述 Agent 模块、数据流、权限隔离和可观测性。
- `docs/specs/api_spec.md`：API 规格，描述 CLI、Benchmark 命令和核心数据结构。

## Architecture

- `docs/architecture.md`：课程报告可复用的架构图、阶段验收标准和系统流程。
- `docs/security_policy.md`：Docker 沙箱权限隔离策略。

## Demo Outputs

- `docs/runs/sample_run.json`：一次完整 Agent 运行报告。
- `docs/runs/benchmark.json`：Benchmark 评估报告。
- `docs/runs/llm_prompt.json`：LLM 测试生成 Prompt 工件。
- `docs/runs/llm_tests.json`：LLM Test Generator Agent dry-run 测试生成报告。
- `docs/runs/review.json`：Code Reviewer Agent 审查报告。
- `docs/runs/fix_plan.json`：Bug Fixer Agent dry-run 修复计划。
- `docs/runs/unit_tests.json`：Unit Test Writer Agent dry-run 单测生成报告。
- `docs/runs/software_engineer.json`：Software Engineer Agent 统一 dry-run 报告。

## Source Code

- `src/main.py`：单项目测试闭环 CLI。
- `src/benchmark.py`：Benchmark 评估 CLI。
- `src/review.py`：代码审查 Agent CLI。
- `src/fix.py`：自动修 Bug Agent CLI。
- `src/unit_tests.py`：缺失覆盖单测生成 Agent CLI。
- `src/engineer.py`：软件工程师 Agent 统一 CLI。
- `src/llm_tests.py`：LLM 测试生成 Agent CLI。
- `src/agents/test_planner.py`：测试规划 Agent。
- `src/agents/test_generator.py`：测试生成 Agent。
- `src/agents/security_checker.py`：生成测试安全检查 Agent。
- `src/agents/result_analyzer.py`：pytest 结果分析 Agent。
- `src/agents/failure_diagnoser.py`：失败诊断与修复建议 Agent。
- `src/agents/code_reviewer.py`：代码审查 Agent。
- `src/agents/bug_fixer.py`：自动修 Bug Agent。
- `src/agents/unit_test_writer.py`：缺失覆盖单测生成 Agent。
- `src/agents/software_engineer.py`：软件工程师 Agent 编排器。
- `src/agents/llm_test_generator.py`：LLM 测试生成 Agent。
- `src/sandbox/docker_executor.py`：Docker 沙箱执行器。
- `src/evaluation/benchmark.py`：Benchmark 汇总逻辑。
- `src/llm/prompt_builder.py`：LLM Prompt 构建器。
- `src/llm/client.py`：OpenAI-compatible LLM 客户端。

## Tests

- `tests/`：单元测试，覆盖测试规划、测试生成、安全检查、结果分析、失败诊断、Benchmark、LLM Prompt 构建、LLM 测试生成、代码审查、自动修 Bug、缺失覆盖单测生成和软件工程师 Agent 编排。

## Demo Script

- `scripts/run_demo.ps1`：Windows PowerShell 一键演示脚本。
