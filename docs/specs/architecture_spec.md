# Architecture Spec

## 1. 架构概览

Software Engineer Agent 采用分层架构：

- CLI 层：`src.engineer`、`src.benchmark`。
- Workflow 层：`src/workflow/software_engineer_graph.py` 中的 LangGraph `StateGraph`。
- Agent 层：LLM 审查、LLM 修复建议、LLM 测试生成、沙箱验证、失败后回跳重试的修复循环和覆盖反馈。
- Tool 层：仓库扫描、临时工作区、报告写出、Prompt 构建和 LLM Client。
- Sandbox 层：local executor 与 Docker executor。

## 2. LangGraph 状态图

```text
START
  -> scan
  -> llm_review
  -> llm_fix_plan
  -> llm_fix
  -> llm_tests / sandbox_validate / coverage_feedback
  -> sandbox_validate / coverage_feedback
  -> repair_loop
  -> llm_fix_plan / llm_tests / coverage_feedback
  -> coverage_feedback
  -> finish
  -> END
```

## 3. 状态对象

`SoftwareEngineerGraphState` 保存：

- `project_path`
- `apply_tests`
- `run_sandbox`
- `sandbox_executor`
- `scan`
- `llm_review`
- `llm_fix_plan`
- `llm_fix`
- `llm_tests`
- `sandbox_validation`
- `repair_loop`
- `coverage_feedback`
- `node_trace`
- `status`

## 4. Agent 职责

- `llm_code_reviewer`: 调用真实 LLM 产生 `LLMCodeReviewReport`。
- `llm_fix_planner`: 从 LLM review findings 和沙箱反馈中选择本轮修复目标，并给出修复顺序。
- `llm_code_fixer`: 调用真实 LLM 产生 `LLMCodeFixReport`，并在 `--apply-fixes` 下写回源码。
- `llm_test_generator`: 调用真实 LLM 产生 `LLMTestGenerationReport`。
- `sandbox_validator`: 在隔离后端运行 pytest，产生 `SandboxValidationReport`。
- `repair_loop`: 根据沙箱失败诊断决定把失败结果回送 `llm_fix_plan` 或 `llm_tests` 重试，或进入覆盖反馈。
- `coverage_feedback`: 汇总覆盖与缺失函数。

## 5. 权限隔离

1. 生成测试先经过 Security Checker。
2. 默认 dry-run，不写回项目。
3. `--apply-tests` 是唯一写回生成测试的开关。
4. Docker executor 使用临时工作区运行 pytest，避免直接污染原项目。

## 6. 观测输出

- `docs/runs/software_engineer.json`
- `docs/runs/software_engineer.md`
- `node_trace`
- 各 Agent 的结构化状态
