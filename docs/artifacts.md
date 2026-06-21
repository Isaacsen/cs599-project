# Project Artifacts

## Specs

- `docs/CS599_大作业报告.md`：最终报告 Markdown 草稿。
- `docs/CS599_大作业报告.pdf`：最终报告 PDF，包含 PDF 大纲书签。
- `docs/specs/product_spec.md`：产品规格，描述问题、用户、功能需求和非功能需求。
- `docs/specs/architecture_spec.md`：架构规格，描述 Agent 模块、数据流、权限隔离和可观测性。
- `docs/specs/api_spec.md`：API 规格，描述 CLI、Benchmark 命令和核心数据结构。
- `实现计划.md`：按当前架构拆分的阶段实现计划。

## Architecture

- `docs/architecture.md`：课程报告可复用的架构图、阶段验收标准和系统流程。
- `docs/security_policy.md`：Docker 沙箱权限隔离策略。
- `docs/final_submission_checklist.md`：最终提交检查清单。

## Demo Outputs

- `docs/runs/software_engineer.json`：Software Engineer Agent LangGraph 主流程 JSON 报告。
- `docs/runs/software_engineer.md`：Software Engineer Agent 可观看 Markdown 报告。
- `docs/runs/software_engineer_graph.json`：显式 LangGraph 入口生成的兼容报告。
- `docs/runs/sample_run.json`：辅助测试流水线运行报告。
- `docs/runs/benchmark.json`：Benchmark 评估报告。
- `docs/runs/llm_prompt.json`：LLM 测试生成 Prompt 工件。
- `docs/runs/llm_tests.json`：LLM Test Generator Agent 测试生成报告。
- `docs/runs/llm_tests_real.json`：真实 DashScope 配置下的 LLM Test Generator 运行报告。
- `docs/runs/review.json`：Code Reviewer Agent 审查报告。
- `docs/runs/fix_plan.json`：Bug Fixer Agent dry-run 修复计划。
- `docs/runs/unit_tests.json`：Unit Test Writer Agent dry-run 单测生成报告。

## Source Code

- `src/engineer.py`：Software Engineer Agent LangGraph 默认 CLI。
- `src/engineer_graph.py`：Software Engineer Agent LangGraph 显式 CLI。
- `src/workflow/software_engineer_graph.py`：LangGraph StateGraph 工作流。
- `src/tools/software_engineer_graph_writer.py`：Software Engineer Agent JSON / Markdown writer。
- `src/main.py`：辅助测试流水线 CLI。
- `src/benchmark.py`：Benchmark 评估 CLI。
- `src/review.py`：代码审查 Agent CLI。
- `src/fix.py`：自动修 Bug Agent CLI。
- `src/unit_tests.py`：缺失覆盖单测生成 Agent CLI。
- `src/llm_tests.py`：LLM 测试生成 Agent CLI。
- `src/agents/code_reviewer.py`：规则代码审查 Agent。
- `src/agents/llm_code_reviewer.py`：真实 LLM 代码审查 Agent。
- `src/agents/bug_fixer.py`：自动修 Bug Agent。
- `src/agents/patch_reviewer.py`：Patch 审查 Agent。
- `src/agents/unit_test_writer.py`：缺失覆盖单测生成 Agent。
- `src/agents/llm_test_generator.py`：LLM 测试生成 Agent。
- `src/agents/sandbox_validator.py`：沙箱验证 Agent。
- `src/agents/repair_loop.py`：修复循环规划 Agent。
- `src/agents/coverage_feedback.py`：覆盖反馈 Agent。
- `src/agents/test_planner.py`：测试规划 Agent。
- `src/agents/test_generator.py`：规则测试生成 Agent。
- `src/agents/security_checker.py`：生成测试安全检查 Agent。
- `src/agents/result_analyzer.py`：pytest 结果分析 Agent。
- `src/agents/failure_diagnoser.py`：失败诊断与修复建议 Agent。
- `src/sandbox/docker_executor.py`：Docker 沙箱执行器。
- `src/sandbox/policy.py`：沙箱策略配置。
- `src/evaluation/benchmark.py`：Benchmark 汇总逻辑。
- `src/llm/prompt_builder.py`：LLM Prompt 构建器。
- `src/llm/client.py`：OpenAI-compatible LLM 客户端。
- `src/llm/config.py`：LLM provider、模型和 API Key 环境变量配置。

## Tests

- `tests/`：单元测试，覆盖测试规划、测试生成、安全检查、结果分析、失败诊断、Benchmark、LLM Prompt 构建、LLM 测试生成、规则代码审查、LLM 代码审查、自动修 Bug、Patch 审查、沙箱验证、修复循环、覆盖反馈、缺失覆盖单测生成和 LangGraph Software Engineer Agent 编排。

## Demo Scripts

- `scripts/run_demo.ps1`：Windows PowerShell 一键演示脚本。
- `scripts/final_verify.ps1`：最终提交前验证脚本。
- `scripts/export_report_pdf.py`：最终报告 PDF 导出脚本。
