# TestGuard Agent

## 项目简介

TestGuard Agent 是一个面向 Python 项目的自动测试生成与权限隔离执行智能体，目标是分析代码仓库、生成 pytest 测试、在受限环境中执行测试，并输出测试结果、失败原因与修复建议。

## 方向

方向一：Agentic AI 原生开发。

## 技术栈

- AI IDE: Trae CN
- LLM: DashScope API / DeepSeek API / OpenAI API / Ollama 本地模型
- Agent 框架: LangGraph
- 测试框架: pytest
- 容器: Docker
- 基础设施: GitHub

当前阶段先不依赖在线大模型，优先完成 SDD 规格初稿、可运行的自动测试执行闭环、Docker 权限隔离执行器、可离线演示的测试规划与生成 Agent、生成代码安全检查、结构化结果分析与 JSON 运行报告、失败诊断建议、LLM Prompt 导出、Benchmark 评估、代码审查 Agent、默认 dry-run 的自动修 Bug Agent、缺失覆盖单测生成 Agent，以及统一的软件工程师 Agent 编排入口。

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
阿里云 DashScope 是默认 LLM provider，代码会优先通过 `os.getenv("DASHSCOPE_API_KEY")` 读取 DashScope Key，并将 `LLM_API_KEY` 作为兼容回退。
如果使用 DeepSeek，可以设置 `LLM_PROVIDER=deepseek`，代码会优先通过 `os.getenv("DEEPSEEK_API_KEY")` 读取 DeepSeek Key。

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

9. 运行代码审查 Agent：

```bash
python -m src.review examples/review_target --output docs/runs/review.json
```

Code Reviewer Agent 会扫描 Python AST，识别危险调用、疑似硬编码密钥、宽泛异常处理、缺失测试覆盖和除零边界风险，并输出结构化 JSON 审查报告。

10. 生成自动修 Bug 计划：

```bash
python -m src.fix examples/review_target --output docs/runs/fix_plan.json
```

Bug Fixer Agent 默认只生成 dry-run 修复计划，不修改目标源码。确认安全后可追加 `--apply`，对目标项目应用已支持的修复规则，例如将 `eval` 替换为 `ast.literal_eval`、将疑似密钥改为环境变量读取、收窄宽泛异常处理，以及加入显式除零保护。

11. 生成缺失覆盖单元测试：

```bash
python -m src.unit_tests examples/review_target --output docs/runs/unit_tests.json
```

Unit Test Writer Agent 默认只生成 dry-run 报告，不写入目标项目。确认后可追加 `--apply`，将生成的 pytest 文件写入目标项目的 `tests/test_testguard_generated.py`。

12. 运行软件工程师 Agent：

```bash
python -m src.engineer examples/review_target --output docs/runs/software_engineer.json
```

Software Engineer Agent 会串联代码审查、自动修 Bug 计划和缺失覆盖单测生成，默认 dry-run，不修改目标项目。需要写回修复或测试时，可分别追加 `--apply-fixes` 或 `--apply-tests`。

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
- [x] Code review agent
- [x] Auto bug fix agent
- [x] Unit test writer agent
- [x] Software engineer agent workflow
- [ ] LLM test generation
- [ ] Final report

## Demo 与交付物

- 报告草稿：`docs/CS599_大作业报告.md`
- Demo 指南：`docs/demo_guide.md`
- 交付物索引：`docs/artifacts.md`
- 一键演示脚本：`scripts/run_demo.ps1`

## 引用与说明

本项目第一阶段代码为课程项目自研实现。后续如果引入开源框架或论文方法，会在本节补充引用来源。
