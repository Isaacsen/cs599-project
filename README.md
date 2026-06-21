# Software Engineer Agent

## 项目简介

Software Engineer Agent 是一个面向 Python 项目的软件工程师 Agent 与权限隔离执行平台。项目使用 LangGraph 编排多个真实 Agent，完成仓库扫描、LLM 代码审查、LLM 修复建议、LLM 测试生成、沙箱验证、失败后回跳重试的修复循环和覆盖反馈，并输出可审计的 JSON / Markdown 报告。

当前版本已移除基于人工规则的 Bug Fix Agent、Patch Review Agent、规则 Review 节点和模板 Unit Test 节点。主流程默认直接使用 LLM Review Agent、LLM Fix Agent 与 LLM Test Agent。

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
│   ├── agents/        # Review, test generation, sandbox, repair, coverage agents
│   ├── llm/           # LLM 配置、Prompt 构建和 OpenAI-compatible client
│   ├── sandbox/       # Local / Docker 执行器与权限隔离策略
│   ├── tools/         # 扫描、工作区和报告写出工具
│   └── workflow/      # LangGraph 主流程
├── tests/
├── scripts/
├── Dockerfile.sandbox
└── requirements.txt
```

## 环境搭建

```bash
python -m venv .venv
pip install -r requirements.txt
```

LLM Key 通过环境变量读取，不要写入代码或文档。默认 provider 为 DashScope：

```bash
DASHSCOPE_API_KEY=your_key
LLM_PROVIDER=dashscope
LLM_MODEL=glm-5.2
```

如需使用 DeepSeek：

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

主流程：

```text
START
  -> scan
  -> llm_review
  -> llm_fix_plan
  -> llm_fix
  -> llm_tests
  -> sandbox_validate / coverage_feedback
  -> sandbox_validate
  -> repair_loop
      -> llm_fix_plan     # code-fix retry first replans selected findings
      -> llm_tests        # 像生成测试自身的问题
      -> llm_tests
      -> coverage_feedback
  -> coverage_feedback
  -> finish
  -> END
```

辅助命令：

```bash
python -m src.llm_tests examples/sample_python_project --output docs/runs/llm_tests.json
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

## 验证

```bash
python -m unittest discover -s tests
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
