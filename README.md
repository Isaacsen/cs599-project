# Software Engineer Agent

## 项目简介

Software Engineer Agent 是一个面向 Python 项目的 LangGraph 多 Agent 软件工程工作流。系统以目标 Python 仓库为输入，完成结构化仓库扫描、真实 LLM 代码审查、修复目标规划、LLM 修复建议、LLM 单测生成、Local / Docker 沙箱验证、失败回跳和覆盖反馈，并输出可审计的 JSON / Markdown 运行报告。

本项目选择课程方向一：Agentic AI 原生开发。当前唯一主入口是 `src.engineer`，评估入口是 `src.benchmark`。旧的辅助 Pipeline、独立 review/unit-test/llm-test CLI 和独立 `docs/specs/` 文件已经移除；Product Spec / Architecture Spec / API Spec 已内嵌到 `docs/CS599_大作业报告.md` 第二章。

## 技术栈

- AI IDE：Codex
- Agent 框架：LangGraph
- LLM：DashScope API / DeepSeek API / OpenAI-compatible API / Ollama
- 默认模型：DashScope `glm-5.2`
- 测试框架：pytest / unittest
- 权限隔离：Docker sandbox、临时工作区、Security Checker、patch safety review
- 语言：Python

## 目录结构

```text
cs599-project/
├── docs/
│   ├── architecture.md
│   ├── CS599_大作业报告.md
│   ├── CS599_大作业报告.pdf
│   └── runs/
├── examples/
├── scripts/
│   ├── export_report_pdf.py
│   ├── final_verify.ps1
│   └── run_demo.ps1
├── src/
│   ├── agents/        # Repo scan, review, fix, test, sandbox, repair, coverage agents
│   ├── evaluation/    # Benchmark 汇总
│   ├── llm/           # LLM 配置、Prompt 构建和 OpenAI-compatible client
│   ├── sandbox/       # Local / Docker 执行器与隔离策略
│   ├── tools/         # 报告写出、临时工作区与兼容导出
│   └── workflow/      # LangGraph 主流程
├── tests/
├── web/
│   └── agent-viewer/  # 静态前端可视化界面
├── Dockerfile.sandbox
├── requirements.txt
└── 课程要求.md
```

## 环境配置

```bash
python -m venv .venv
pip install -r requirements.txt
```

默认使用 DashScope：

```bash
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_key
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

## 运行方式

基础 dry-run：

```bash
python -m src.engineer examples/review_target
```

启用 Docker 沙箱验证：

```bash
python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --docker-image software-engineer-agent-python:latest
```

指定报告输出：

```bash
python -m src.engineer examples/review_target --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
```

运行后还会生成前端可读取的事件日志：

```text
docs/runs/software_engineer_events.jsonl
```

写回修复和测试需要显式开启：

```bash
python -m src.engineer examples/review_target --apply-fixes --apply-tests --run-sandbox
```

默认会输出 `[agent-stream]` 节点进度和 `[llm-stream]` token 级模型输出。安静模式：

```bash
python -m src.engineer examples/review_target --no-stream --no-llm-token-stream
```

## 前端可视化

项目提供一个无构建依赖的静态 Web Viewer，用于展示 Agent 状态图、节点 Timeline 和每轮中间输出。

先运行一次 Agent 生成报告和事件日志：

```bash
python -m src.engineer examples/review_target --run-sandbox --sandbox-executor local
```

启动静态服务器：

```bash
python -m http.server 8000
```

浏览器打开：

```text
http://localhost:8000/web/agent-viewer/
```

Viewer 会读取：

- `docs/runs/software_engineer.json`
- `docs/runs/software_engineer_events.jsonl`
- `docs/runs/software_engineer.md`

## 常用参数

| 参数 | 说明 |
| --- | --- |
| `project_path` | 待审查 Python 项目路径。 |
| `--output` | JSON 运行报告路径，默认 `docs/runs/software_engineer.json`。 |
| `--output-md` | Markdown 运行报告路径，默认 `docs/runs/software_engineer.md`。 |
| `--events-output` | Agent 事件 JSONL 路径，默认 `docs/runs/software_engineer_events.jsonl`。 |
| `--apply-fixes` | 将 LLM 修复建议写回源码，默认 dry-run。 |
| `--apply-tests` | 将 LLM 生成测试写回项目，默认 dry-run。 |
| `--run-sandbox` | 启用沙箱验证。 |
| `--sandbox-executor` | `local` 或 `docker`，默认 `docker`。 |
| `--docker-image` | Docker 沙箱镜像。 |
| `--timeout` | 沙箱执行超时，默认 30 秒。 |
| `--llm-timeout` | 单次 LLM 请求超时。 |
| `--llm-retries` | LLM 请求重试次数。 |
| `--repair-iterations` | repair loop 最大重试次数，默认 3。 |
| `--llm-test-file` | LLM 生成测试写回路径。 |
| `--max-functions` | 生成测试时最多考虑的公开函数数。 |
| `--no-stream` | 关闭 Agent 级流式进度。 |
| `--no-llm-token-stream` | 关闭 token 级 LLM 输出。 |

## Agent 工作流

```text
目标 Python 仓库
  -> Repo Scan Agent
  -> LLM Code Review Agent
  -> LLM Fix Planner Agent
  -> LLM Code Fix Agent
  -> LLM Test Writer Agent
  -> Local / Docker Sandbox Validator Agent
  -> Repair Loop Agent
  -> Coverage Feedback Agent
  -> JSON / Markdown 运行报告
```

Repo Scan Agent 会在终端输出结构化 stream，例如：

```json
{"status":"scanned","source_files":1,"test_files":0,"config_files":0,"dependency_files":0,"package_roots":0,"entry_points":0,"issues":[],"error_summary":""}
```

## Benchmark

```bash
python -m src.benchmark --executor local --output docs/runs/benchmark.json
```

Docker benchmark：

```bash
python -m src.benchmark --executor docker --docker-image software-engineer-agent-python:latest --output docs/runs/benchmark.json
```

## 验证

```bash
python -m pytest tests -q
python -m compileall src tests examples
python -m src.engineer examples/review_target --no-stream --no-llm-token-stream
```

Windows PowerShell：

```powershell
scripts/final_verify.ps1
```

## 文档与交付物

- `docs/CS599_大作业报告.md`：课程最终报告源文件，包含封面、目录、七章正文，以及内嵌 Product Spec / Architecture Spec / API Spec。
- `docs/CS599_大作业报告.pdf`：由 `scripts/export_report_pdf.py` 导出的最终 PDF 报告，包含书签导航。
- `docs/architecture.md`：项目架构和 LangGraph 工作流说明。
- `docs/runs/software_engineer.json`：主 Agent JSON 运行报告。
- `docs/runs/software_engineer.md`：主 Agent Markdown 运行报告。
- `docs/runs/software_engineer_events.jsonl`：前端可视化读取的结构化 Agent 事件日志。
- `docs/runs/software_engineer_agent_flow.png`：LangGraph Agent 流程图。
- `docs/runs/benchmark.json`：Benchmark 输出。
- `web/agent-viewer/`：展示状态图、Timeline 和每轮中间输出的静态前端。

## 项目状态

- [x] LangGraph 多 Agent 主流程
- [x] Repo Scan Agent 结构化输出
- [x] LLM Review / Fix / Test Agent
- [x] Repair loop 回跳
- [x] Local / Docker sandbox 验证
- [x] JSON / Markdown / PDF 报告
- [x] Benchmark 与单元测试
- [ ] 报告封面中的学号、姓名、专业待最终填写
