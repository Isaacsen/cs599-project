# TestGuard Agent

## 项目简介

TestGuard Agent 是一个面向 Python 项目的自动测试生成与权限隔离执行智能体，目标是分析代码仓库、生成 pytest 测试、在受限环境中执行测试，并输出测试结果、失败原因与修复建议。

## 方向

方向一：Agentic AI 原生开发。

## 技术栈

- AI IDE: Trae CN
- LLM: DeepSeek API / OpenAI API / Ollama 本地模型
- Agent 框架: LangGraph
- 测试框架: pytest
- 容器: Docker
- 基础设施: GitHub

当前阶段先不依赖在线大模型，优先完成 SDD 规格初稿、可运行的自动测试执行闭环、Docker 权限隔离执行器、可离线演示的测试规划与生成 Agent、生成代码安全检查、结构化结果分析与 JSON 运行报告、失败诊断建议、LLM Prompt 导出，以及可重复运行的 Benchmark 评估。

## 目录结构

```text
cs599-project/
├── docs/
│   ├── architecture.md
│   └── specs/
│       ├── product_spec.md
│       ├── architecture_spec.md
│       └── api_spec.md
├── examples/
│   └── sample_python_project/
├── src/
│   ├── agents/
│   ├── sandbox/
│   ├── tools/
│   └── workflow/
├── Dockerfile.sandbox
├── README.md
├── requirements.txt
└── .env.example
```

## 环境搭建

1. 创建虚拟环境：

```bash
python -m venv .venv
```

2. 激活虚拟环境并安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置环境变量：

```bash
cp .env.example .env
```

不要在代码中硬编码 API Key。

4. 运行最小闭环 Demo：

```bash
python -m src.main examples/sample_python_project
```

预期输出会包含项目路径、源码文件数量、测试文件数量、测试是否通过、耗时以及 pytest 输出。

5. 可选：构建并使用 Docker 沙箱执行测试：

```bash
docker build -f Dockerfile.sandbox -t testguard-python .
python -m src.main examples/sample_python_project --executor docker
```

Docker 执行器需要本机 Docker daemon 正常运行。它默认启用网络禁用、只读源码挂载、只读根文件系统、CPU/内存/进程数限制和执行超时。

6. 生成测试并在沙箱中执行：

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker
```

当前 Test Planner Agent 会分析 Python AST，识别公开函数并生成结构化测试计划；Test Generator Agent 再按计划生成 pytest 测试到临时工作区执行，不会修改原始项目源码。后续可将规则型 Planner / Generator 替换为 LLM Agent。
生成后的测试会先经过 Security Checker Agent，拦截危险 import 和 `eval` / `exec` 等高风险调用。

7. 保存结构化运行报告：

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker --report-json docs/runs/sample_run.json
```

JSON 报告包含仓库扫描结果、执行后端、pytest 汇总、生成测试信息和运行耗时，可用于最终报告中的测试评估与可观测性展示。
当测试失败或超时时，报告会额外包含诊断状态、失败类型、关键线索和修复建议。

还可以导出 LLM 测试生成 Prompt：

```bash
python -m src.main examples/sample_python_project --generate-tests --export-llm-prompt docs/runs/llm_prompt.json
```

导出的 Prompt 包含系统约束、测试计划和源码上下文，不包含 API Key 明文。

8. 运行 Benchmark 评估：

```bash
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

Benchmark 会运行默认样例项目，统计用例通过率、pytest 用例数量、规划测试数量、生成测试数量和总耗时，输出可用于最终报告的评估 JSON。

## 项目状态

- [x] Proposal
- [x] MVP skeleton
- [x] Docker sandbox executor
- [x] Offline test planning agent
- [x] Offline test generation agent
- [x] Generated test security checker
- [x] Result analysis and JSON trace
- [x] Failure diagnosis suggestions
- [x] LLM prompt export
- [x] Benchmark evaluation
- [x] Demo guide and artifacts index
- [ ] LLM test generation
- [ ] Final report

## Demo 与交付物

- Demo 指南：`docs/demo_guide.md`
- 交付物索引：`docs/artifacts.md`
- 一键演示脚本：`scripts/run_demo.ps1`

## 引用与说明

本项目第一阶段代码为课程项目自研实现。后续如果引入开源框架或论文方法，会在本节补充引用来源。
