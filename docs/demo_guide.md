# Software Engineer Agent Demo Guide

## Demo 目标

本 Demo 展示 Software Engineer Agent 的完整闭环：

```text
Python 项目
  -> Repo Scanner
  -> Rule Code Reviewer Agent
  -> LLM Code Reviewer Agent
  -> Bug Fixer Agent
  -> Patch Reviewer Agent
  -> Unit Test Writer Agent
  -> LLM Test Generator Agent
  -> Docker Sandbox Validator Agent
  -> Repair Loop Agent
  -> Coverage Feedback Agent
  -> JSON / Markdown Report
```

## 准备步骤

1. 构建 Docker 沙箱镜像：

```bash
docker build -f Dockerfile.sandbox -t software-engineer-agent-python .
```

2. 运行单元测试：

```bash
python -m unittest discover -s tests
```

3. 运行语法编译检查：

```bash
python -m compileall src tests examples
```

## 核心演示命令

### 1. 运行软件工程师 Agent

```bash
python -m src.engineer examples/review_target --use-llm-review --use-llm-tests --run-sandbox --sandbox-executor docker --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
```

演示要点：

- 使用 LangGraph StateGraph 串联规则审查、LLM 审查、自动修 Bug 计划、Patch 审查、单测生成、LLM 测试生成、Docker 沙箱验证、修复循环和覆盖反馈。
- 默认 dry-run，不修改样例源码。
- 统一 JSON 报告写入 `docs/runs/software_engineer.json`。
- 可观看 Markdown 报告写入 `docs/runs/software_engineer.md`。

### 2. 自动生成测试并在 Docker 沙箱执行

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker --report-json docs/runs/sample_run.json
```

演示要点：

- 自动识别 `calculator.add` 和 `calculator.divide`。
- 生成 2 个测试计划项。
- 生成 2 个 pytest 测试。
- Security Checker 显示 `passed`。
- Docker 沙箱执行结果为 `5 passed`。
- JSON 报告写入 `docs/runs/sample_run.json`。

### 3. 导出 LLM Prompt

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker --export-llm-prompt docs/runs/llm_prompt.json
```

演示要点：

- Prompt 包含 system 安全约束。
- Prompt 包含 TestPlan 和源码上下文。
- Prompt 工件不包含 API Key 明文，只记录 `api_key_set`。

### 4. 运行 Benchmark

```bash
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

演示要点：

- 输出总用例数、通过用例数、通过率。
- 输出 pytest 用例数量、规划测试数量、生成测试数量。
- Benchmark JSON 可作为最终报告的测试与评估证据。

### 5. 运行代码审查 Agent

```bash
python -m src.review examples/review_target --output docs/runs/review.json
```

演示要点：

- 扫描 `examples/review_target` 中的风险样例。
- 识别危险调用、疑似硬编码密钥、宽泛异常处理、缺失测试覆盖和除零边界风险。
- 审查报告写入 `docs/runs/review.json`。

### 6. 生成自动修 Bug 计划

```bash
python -m src.fix examples/review_target --output docs/runs/fix_plan.json
```

演示要点：

- 默认 dry-run，不修改样例源码。
- 输出可应用的安全修复，包括 `eval` 替换、环境变量读取、异常收窄和除零保护。
- 修复计划写入 `docs/runs/fix_plan.json`。

### 7. 生成缺失覆盖单元测试

```bash
python -m src.unit_tests examples/review_target --output docs/runs/unit_tests.json
```

演示要点：

- 默认 dry-run，不修改样例源码。
- 识别缺失测试覆盖的公开函数。
- 生成 pytest 测试内容，并通过 Security Checker。
- 单测生成报告写入 `docs/runs/unit_tests.json`。

### 8. 运行 LLM 测试生成 Agent

```bash
python -m src.llm_tests examples/sample_python_project --output docs/runs/llm_tests.json
```

演示要点：

- LLM Demo 使用环境变量中的真实 provider 配置。
- 使用环境变量中的 DashScope / DeepSeek 配置进行真实 LLM 调用。
- 生成的 pytest 内容经过 Security Checker。
- LLM 测试生成报告写入 `docs/runs/llm_tests.json`。

## 5 分钟展示建议

1. 30 秒：介绍问题，说明人工写测试成本高，LLM 生成测试需要权限隔离。
2. 60 秒：展示架构图和 Agent 流程。
3. 90 秒：运行 Software Engineer Agent，展示 Agent Timeline。
4. 60 秒：打开 `software_engineer.md` 或 `software_engineer.json`，展示多 Agent 交互、沙箱验证和覆盖反馈。
5. 40 秒：运行 Benchmark 或展示 `benchmark.json`。
6. 30 秒：运行代码审查或展示 `review.json`。
7. 30 秒：展示 `fix_plan.json`，说明自动修 Bug 默认 dry-run。
8. 30 秒：展示 `unit_tests.json`，说明缺失覆盖单测生成默认 dry-run。
9. 30 秒：运行软件工程师 Agent 或展示 `software_engineer.json`。
10. 30 秒：运行 LLM 测试生成或展示 `llm_tests.json`。
11. 20 秒：展示 `llm_prompt.json`，说明 Prompt 与真实 LLM 调用链路。

## 兜底方案

如果现场 Docker 不可用，可以展示已提交的 JSON 工件：

- `docs/runs/sample_run.json`
- `docs/runs/benchmark.json`
- `docs/runs/llm_prompt.json`
- `docs/runs/llm_tests.json`
- `docs/runs/review.json`
- `docs/runs/fix_plan.json`
- `docs/runs/unit_tests.json`
- `docs/runs/software_engineer.json`
- `docs/runs/software_engineer_graph.json`

这些文件记录了完整 Demo 的可复现输出。

## 提交前验证

最终提交前可以运行：

```powershell
scripts/final_verify.ps1
```

该脚本会执行单元测试、语法编译检查、LangGraph 软件工程师 Agent dry-run、真实 LLM 测试生成、PDF 导出检查，以及明文 API Key 扫描。
