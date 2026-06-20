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
- `docs/runs/review.json`：Code Reviewer Agent 审查报告。

## Source Code

- `src/main.py`：单项目测试闭环 CLI。
- `src/benchmark.py`：Benchmark 评估 CLI。
- `src/review.py`：代码审查 Agent CLI。
- `src/agents/test_planner.py`：测试规划 Agent。
- `src/agents/test_generator.py`：测试生成 Agent。
- `src/agents/security_checker.py`：生成测试安全检查 Agent。
- `src/agents/result_analyzer.py`：pytest 结果分析 Agent。
- `src/agents/failure_diagnoser.py`：失败诊断与修复建议 Agent。
- `src/agents/code_reviewer.py`：代码审查 Agent。
- `src/sandbox/docker_executor.py`：Docker 沙箱执行器。
- `src/evaluation/benchmark.py`：Benchmark 汇总逻辑。
- `src/llm/prompt_builder.py`：LLM Prompt 构建器。

## Tests

- `tests/`：单元测试，覆盖测试规划、测试生成、安全检查、结果分析、失败诊断、Benchmark、LLM Prompt 构建和代码审查。

## Demo Script

- `scripts/run_demo.ps1`：Windows PowerShell 一键演示脚本。
