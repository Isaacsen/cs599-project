# Software Engineer Agent Demo Guide

## Demo 目标

本 Demo 展示 Software Engineer Agent 的完整闭环：

```text
Python 项目
  -> Repo Scanner
  -> LLM Code Reviewer Agent
  -> LLM Test Generator Agent
  -> Docker Sandbox Validator Agent
  -> Repair Loop Agent
  -> Coverage Feedback Agent
  -> JSON / Markdown Report
```

项目已移除基于人工规则的 Bug Fix Agent、Patch Review Agent、规则 Review 节点和模板 Unit Test 节点，因此 Demo 直接展示 LLM Agent 审查、LLM Agent 测试生成和沙箱验证。

## 准备步骤

```bash
docker build -f Dockerfile.sandbox -t software-engineer-agent-python .
python -m unittest discover -s tests
python -m compileall src tests examples
```

## 核心演示命令

### 1. 运行软件工程师 Agent

```bash
python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
```

演示要点：

- LangGraph StateGraph 串联 LLM 审查、LLM 测试生成、Docker 沙箱验证、修复循环和覆盖反馈。
- 默认 dry-run，不修改样例源码。
- JSON 报告写入 `docs/runs/software_engineer.json`。
- Markdown 报告写入 `docs/runs/software_engineer.md`。

### 2. 自动生成测试并在 Docker 沙箱执行

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker --report-json docs/runs/sample_run.json
```

演示要点：

- 自动识别公开函数。
- 生成 pytest 测试。
- Security Checker 检查生成代码。
- Docker 沙箱执行测试。

### 3. 导出 LLM Prompt

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker --export-llm-prompt docs/runs/llm_prompt.json
```

演示要点：

- Prompt 包含 system 安全约束、TestPlan 和源码上下文。
- 工件不包含 API Key 明文，只记录 `api_key_set` 和 `api_key_env`。

### 4. 运行 Benchmark

```bash
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

### 5. 运行 LLM 测试生成 Agent

```bash
python -m src.llm_tests examples/sample_python_project --output docs/runs/llm_tests.json
```

## 5 分钟展示建议

1. 30 秒：说明问题，人工写测试成本高，LLM 生成测试需要权限隔离。
2. 60 秒：展示架构图和 Agent 流程。
3. 90 秒：运行 Software Engineer Agent，展示 Agent Timeline。
4. 60 秒：打开 `software_engineer.md` 或 `software_engineer.json`，展示多 Agent 交互、沙箱验证和覆盖反馈。
5. 40 秒：运行 Benchmark 或展示 `benchmark.json`。
6. 30 秒：展示 `llm_tests.json`。
7. 20 秒：展示 `llm_prompt.json`，说明 Prompt 与真实 LLM 调用链路。

## 兜底方案

如果现场 Docker 或 LLM 不可用，可以展示已提交的 JSON 工件：

- `docs/runs/sample_run.json`
- `docs/runs/benchmark.json`
- `docs/runs/llm_prompt.json`
- `docs/runs/llm_tests.json`
- `docs/runs/software_engineer.json`

## 提交前验证

```powershell
scripts/final_verify.ps1
```
