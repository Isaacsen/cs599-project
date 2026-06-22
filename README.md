# Software Engineer Agent

## 项目简介

Software Engineer Agent 是一个面向 Python 项目的软件工程师 Agent 与权限隔离执行平台。项目使用 LangGraph 编排真实 Agent，完成仓库扫描、LLM 代码审查、修复规划、LLM 修复、LLM 测试生成、沙箱验证、失败后回跳修复以及覆盖反馈，并输出可审计的 JSON / Markdown 报告。

当前主入口为 `src.engineer`。旧的辅助 Pipeline 和独立 CLI 入口已经移除，项目默认围绕“软件工程师 Agent 工作流”运行。

## 技术栈

- Agent 框架：LangGraph
- LLM：DashScope API / DeepSeek API / OpenAI-compatible API / Ollama
- 测试框架：pytest / unittest
- 权限隔离：Docker sandbox、临时工作区、生成代码安全检查
- 语言：Python

## 目录结构

```text
cs599-project/
├── docs/
│   ├── architecture.md
│   ├── CS599_大作业报告.md
│   ├── CS599_大作业报告.pdf
│   ├── specs/
│   └── runs/
├── examples/
├── src/
│   ├── agents/        # repo scan, review, fix, test, sandbox, repair, coverage agents
│   ├── llm/           # LLM 配置、Prompt 构建和 OpenAI-compatible client
│   ├── sandbox/       # Local / Docker 执行器与权限隔离策略
│   ├── tools/         # 报告写出、工作区与兼容工具
│   └── workflow/      # LangGraph 主流程
├── tests/
├── scripts/
├── Dockerfile.sandbox
└── requirements.txt
```

## 环境配置

```bash
python -m venv .venv
pip install -r requirements.txt
```

默认 provider 为 DashScope：

```bash
DASHSCOPE_API_KEY=your_key
LLM_PROVIDER=dashscope
LLM_MODEL=glm-5.2
```

使用 DeepSeek：

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key
LLM_MODEL=deepseek-v4-pro
```

构建 Docker 沙箱镜像：

```bash
docker build -f Dockerfile.sandbox -t software-engineer-agent-python .
```

## 运行主 Agent

```bash
python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --docker-image software-engineer-agent-python:latest --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
```

如需把修复和测试写回目标项目，显式增加：

```bash
--apply-fixes --apply-tests
```

默认会输出 `[agent-stream]` 节点进度和 `[llm-stream]` token 级模型输出；如需安静输出：

```bash
--no-stream --no-llm-token-stream
```

主流程：

```text
START
  -> scan
  -> llm_review
  -> llm_fix_plan
  -> llm_fix
  -> llm_tests
  -> sandbox_validate / coverage_feedback
  -> repair_loop
      -> llm_fix_plan
      -> llm_tests
      -> coverage_feedback
  -> finish
  -> END
```

## 验证

```bash
python -m pytest tests
python -m compileall src tests examples
```

Windows PowerShell：

```powershell
scripts/final_verify.ps1
```

## 交付物

- `docs/CS599_大作业报告.md`
- `docs/CS599_大作业报告.pdf`
- `docs/architecture.md`
- `docs/specs/product_spec.md`
- `docs/specs/architecture_spec.md`
- `docs/specs/api_spec.md`
- `docs/runs/software_engineer.json`
- `docs/runs/software_engineer.md`
- `docs/runs/software_engineer_agent_flow.png`
