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

当前第一步实现先不接入大模型，优先完成 SDD 规格初稿与可运行的自动测试执行闭环。

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

## 项目状态

- [x] Proposal
- [x] MVP skeleton
- [ ] LLM test generation
- [ ] Docker sandbox
- [ ] Final report

## 引用与说明

本项目第一阶段代码为课程项目自研实现。后续如果引入开源框架或论文方法，会在本节补充引用来源。
