# Product Spec: TestGuard Agent

## 1. 项目背景

企业级软件项目需要持续测试来保障质量，但人工编写测试存在成本高、覆盖不足、回归测试维护困难等问题。LLM 可以帮助生成测试用例，但直接执行模型生成的代码存在文件破坏、网络访问、资源耗尽和敏感信息泄露风险。

TestGuard Agent 目标是构建一个面向 Python 项目的自动测试智能体：它能够理解项目结构，规划并生成 pytest 测试，在权限隔离环境中执行测试，最后输出结构化报告和修复建议。

## 2. 用户角色

- 开发者：希望快速获得测试用例、测试结果和失败诊断。
- 课程评审者：希望看到 Agentic AI、SDD、工具调用、状态管理和权限隔离的完整工程闭环。

## 3. 核心目标

1. 扫描 Python 项目并识别源码文件、测试文件和测试框架。
2. 生成面向核心函数和边界场景的 pytest 测试计划。
3. 通过 LLM Agent 生成测试代码。
4. 在沙箱环境中执行测试，限制文件写入、网络访问、CPU、内存和执行时间。
5. 分析测试结果，输出失败原因、覆盖率信息和修复建议。
6. 执行代码审查，发现危险调用、疑似硬编码密钥、异常处理和测试覆盖风险。
7. 生成自动修 Bug 计划，并在用户显式确认时应用安全修复。
8. 为缺失覆盖的公开函数生成单元测试，并在用户显式确认时写入目标项目。
9. 通过统一软件工程师 Agent 编排代码审查、修复计划和单测生成。
10. 接入 OpenAI-compatible LLM 测试生成，支持 DashScope、DeepSeek 等 provider。

## 4. 第一阶段范围

第一阶段不接入 LLM，先实现可运行的最小闭环：

```text
输入 Python 项目路径 -> 扫描项目 -> 执行已有 pytest 测试 -> 输出结构化结果
```

完成该闭环后，再逐步加入测试规划 Agent、测试生成 Agent 和 Docker 权限隔离。

第二阶段实现 Docker 权限隔离执行器：

```text
输入 Python 项目路径 -> 扫描项目 -> 在 Docker 沙箱中执行 pytest -> 输出结构化结果
```

第三阶段加入可离线演示的规则型 Test Planner Agent 与 Test Generator Agent：

```text
输入 Python 项目路径 -> 扫描项目 -> 分析 AST -> 生成测试计划 -> 生成 pytest 测试 -> 临时工作区执行 -> 输出结构化结果
```

该阶段仍不依赖在线 API，目的是先验证自动测试生成闭环，后续再将规则型生成器替换为 LLM 生成器。

第四阶段加入结果分析与 JSON 运行报告：

```text
pytest 输出 -> Result Analyzer Agent -> 测试统计汇总 -> JSON trace -> 评估证据
```

第五阶段加入 Benchmark 评估：

```text
Benchmark Cases -> Pipeline Runs -> Metrics Aggregation -> Benchmark JSON Report
```

第六阶段加入失败诊断：

```text
pytest 输出 + PytestSummary -> Failure Diagnosis -> key findings + suggestions
```

第七阶段显式化安全检查：

```text
Generated Test Code -> Security Checker -> SecurityCheckResult -> PipelineReport
```

第八阶段加入 LLM Prompt 导出：

```text
TestPlan + Source Context -> LLM Prompt Builder -> Prompt JSON Artifact
```

第九阶段加入代码审查 Agent：

```text
Python Source -> Code Reviewer Agent -> ReviewFinding List -> Review JSON Report
```

第十阶段加入自动修 Bug Agent：

```text
Python Source -> Bug Fixer Agent -> FixPlan -> Optional Apply
```

第十一阶段加入缺失覆盖单测生成 Agent：

```text
Python Source + Existing Tests -> Unit Test Writer Agent -> Generated Pytest Suite -> Optional Apply
```

第十二阶段加入软件工程师 Agent 编排：

```text
Python Project -> Software Engineer Agent -> ReviewReport + FixPlan + UnitTestReport
```

第十三阶段加入 LLM 测试生成 Agent：

```text
TestPlan + Source Context -> LLM Test Generator Agent -> SecurityCheckResult -> LLM Test Report
```

## 5. 功能需求

### FR-1 项目扫描

系统应接收本地项目路径，递归扫描 `.py` 文件，并区分源码文件与测试文件。

### FR-2 测试执行

系统应调用 pytest 执行目标项目测试，并捕获 stdout、stderr、退出码和耗时。

### FR-3 超时控制

系统应为测试执行设置超时时间，避免死循环或长期阻塞。

### FR-4 报告输出

系统应输出可读的命令行报告，包含语言、测试框架、源码文件数量、测试文件数量、测试结果和耗时。

### FR-5 后续 Agent 扩展

系统应预留 Agent 模块边界，后续支持 Repo Analyzer、Test Planner、Test Generator、Result Analyzer 等角色。

### FR-6 Docker 权限隔离执行

系统应提供 Docker 执行后端，支持网络禁用、只读挂载、资源限制和超时控制。

### FR-7 自动测试生成

系统应在用户启用 `--generate-tests` 时扫描源码中的公开函数，生成结构化测试计划和 pytest 测试文件，并在临时项目副本中执行测试，避免修改原始源码。

### FR-8 测试规划

系统应为公开函数生成测试计划，包含目标函数、测试场景和设计理由，为后续 LLM Agent 和评估提供可解释中间产物。

### FR-9 生成代码安全校验

系统应对生成的测试代码进行 AST 校验，禁止导入 `subprocess`、`socket`、`requests` 等高风险模块。

### FR-10 结果分析与可观测性

系统应解析 pytest 输出，提取 passed、failed、errors、skipped、warnings、total 和 conclusion，并支持将一次运行保存为 JSON 报告。

### FR-11 Benchmark 评估

系统应提供可重复运行的 Benchmark 入口，统计测试通过率、pytest 用例数量、规划测试数量、生成测试数量和总耗时，并输出 JSON 评估报告。

### FR-12 失败诊断与修复建议

系统应在测试失败、执行错误或超时时，提取 pytest 输出中的失败线索，分类失败类型，并给出面向开发者的修复建议。

### FR-13 生成测试安全检查

系统应将生成测试代码的 AST 安全检查显式建模为 Agent 输出，报告是否通过、违规规则、违规内容和所在行号。

### FR-14 LLM Prompt 导出

系统应能基于测试计划和源码上下文导出 LLM 测试生成 Prompt，便于后续接入 DashScope、DeepSeek、OpenAI 或本地模型，同时不得写出 API Key 明文。

### FR-15 代码审查

系统应提供独立的代码审查 Agent，基于 Python AST 识别危险调用、疑似硬编码密钥、宽泛异常处理、缺失测试覆盖和除零边界风险，并输出结构化审查报告。

### FR-16 自动修 Bug

系统应提供自动修 Bug Agent，默认以 dry-run 方式生成结构化修复计划，并在用户显式传入 `--apply` 时应用安全规则修复，例如替换危险 `eval`、改用环境变量读取疑似密钥、收窄宽泛异常处理和加入除零保护。

### FR-17 缺失覆盖单测生成

系统应提供 Unit Test Writer Agent，识别现有测试未覆盖的公开函数，生成 pytest 单元测试内容并通过安全检查；默认只输出 dry-run JSON 报告，用户显式传入 `--apply` 后才写入目标项目。

### FR-18 软件工程师 Agent 编排

系统应提供统一的软件工程师 Agent 入口，串联代码审查、自动修 Bug 计划和缺失覆盖单测生成，输出统一 JSON 报告；默认 dry-run，不修改目标项目，用户可通过独立开关启用修复或测试写回。

### FR-19 LLM 测试生成

系统应提供 LLM Test Generator Agent，基于 TestPlan 和源码上下文调用 OpenAI-compatible Chat Completions 接口生成 pytest 代码，支持 DashScope、DeepSeek 等 provider；生成代码必须经过 Security Checker，报告不得包含 API Key 明文，并支持离线 mock response 演示。

## 6. 非功能需求

- 安全性：不得硬编码 API Key，敏感配置必须通过环境变量读取。
- 可扩展性：测试执行器应可从本地执行替换为 Docker 沙箱执行。
- 可观测性：每次测试运行应保留结构化结果，并可导出 JSON trace。
- 可维护性：模块边界清晰，代码遵循简单、可测试、低耦合原则。

## 7. 课程要求映射

- SDD 规格驱动开发：Product Spec、Architecture Spec、API Spec。
- 工具使用 / Function Calling：项目扫描、测试执行、代码审查和报告生成均设计为可被 Agent 调用的工具。
- 状态管理与多步骤推理：后续使用 LangGraph 编排扫描、规划、生成、执行、分析流程。
- 可观测性与评估：记录测试结果、耗时、退出码、通过率和失败原因。
- 权限隔离：通过 Docker 实现网络禁用、只读挂载、资源限制和超时控制。
