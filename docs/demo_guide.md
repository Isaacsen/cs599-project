# Software Engineer Agent Demo Guide

## Demo 目标

本 Demo 展示 Software Engineer Agent 的完整闭环：

```text
Python 项目
  -> Repo Scan Agent
  -> LLM Code Review Agent
  -> LLM Fix Planner Agent
  -> LLM Code Fix Agent
  -> LLM Test Writer Agent
  -> Docker Sandbox Validator Agent
  -> Repair Loop Agent
  -> Coverage Feedback Agent
  -> JSON / Markdown Report
```

项目现在只保留 `src.engineer` 作为主入口。旧的辅助 Pipeline、独立 review/unit-test/llm-test CLI 已经移除。

## 准备步骤

```bash
docker build -f Dockerfile.sandbox -t software-engineer-agent-python .
python -m pytest tests
python -m compileall src tests examples
```

## 核心演示命令

### 1. 运行完整软件工程师 Agent

```bash
python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
```

演示要点：
- LangGraph 串联 repo scan、LLM review、fix plan、LLM fix、LLM tests、sandbox validate、repair loop 和 coverage feedback。
- 默认 dry-run，不修改样例源码。
- 默认输出 `[agent-stream]` 和 `[llm-stream]`，方便观察长时间 LLM 调用。
- JSON 报告写入 `docs/runs/software_engineer.json`。
- Markdown 报告写入 `docs/runs/software_engineer.md`。

### 2. 演示写回模式

```bash
python -m src.engineer examples/review_target --apply-fixes --apply-tests --run-sandbox --sandbox-executor docker
```

演示要点：
- 只有显式开启 `--apply-fixes` 与 `--apply-tests` 才会写回目标项目。
- 代码修复写回前会经过 patch safety review。
- 生成测试会先经过安全检查，再进入沙箱验证。

### 3. 运行 Benchmark

```bash
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

Benchmark 现在基于当前 LangGraph 软件工程师 Agent 运行，不再依赖旧 Pipeline。

## 5 分钟展示建议

1. 30 秒：说明问题，LLM 自动审查和修复需要可观察流程与权限隔离。
2. 60 秒：展示架构图和 Agent 流程图。
3. 90 秒：运行 `src.engineer`，观察 Agent Timeline 与 token stream。
4. 60 秒：打开 `software_engineer.md` 或 `software_engineer.json`，展示多 Agent 交互、沙箱验证和覆盖反馈。
5. 40 秒：展示 Benchmark 或 `benchmark.json`。
6. 40 秒：说明 repo scan agent、结构化失败报告和 dry-run/write-back 边界。

## 兜底方案

如果现场 Docker 或 LLM 不可用，可以展示已提交的报告文件：

- `docs/runs/software_engineer.json`
- `docs/runs/software_engineer.md`
- `docs/runs/benchmark.json`
- `docs/runs/software_engineer_agent_flow.png`

## 提交前验证

```powershell
scripts/final_verify.ps1
```
