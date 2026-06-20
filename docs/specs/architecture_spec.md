# Architecture Spec: TestGuard Agent

## 1. 架构目标

TestGuard Agent 采用分层架构，将代码理解、测试规划、测试生成、隔离执行、结果分析和代码审查解耦。第一阶段实现仓库扫描与本地测试执行，第二阶段加入 Docker 沙箱执行器，第三阶段加入可离线演示的测试规划与生成 Agent，第四阶段加入结果分析与 JSON 运行报告，第五阶段加入 Benchmark 评估，第六阶段加入失败诊断与修复建议，第七阶段显式化生成测试安全检查，第八阶段加入 LLM Prompt 导出，第九阶段加入代码审查 Agent。

## 2. 总体流程

```text
Repo Scanner
  -> Test Planning Agent
  -> Test Generation Agent
  -> Security Checker
  -> Sandbox Executor
  -> Result Analyzer Agent
  -> Report Generator
```

第一阶段实际流程：

```text
Repo Scanner
  -> Local Pytest Executor
  -> Console Report
```

第二阶段实际流程：

```text
Repo Scanner
  -> Docker Sandbox Executor
  -> Console Report
```

第四阶段实际流程：

```text
Repo Scanner
  -> Rule-based Test Planner Agent
  -> Rule-based Test Generator Agent
  -> Generated Test Security Check
  -> Temporary Test Workspace
  -> Local / Docker Executor
  -> Result Analyzer Agent
  -> Failure Diagnoser Agent
  -> JSON Trace Writer
  -> Console Report
```

第五阶段评估流程：

```text
Benchmark Cases
  -> Pipeline Runs
  -> Benchmark Aggregator
  -> Benchmark JSON Report
```

第八阶段 LLM 准备流程：

```text
TestPlan
  -> Source Context Collector
  -> LLM Prompt Builder
  -> Prompt JSON Artifact
```

第九阶段代码审查流程：

```text
Repo Scanner
  -> Code Reviewer Agent
  -> Review JSON Writer
  -> CLI Review Report
```

## 3. 模块设计

### 3.1 Repo Scanner

位置：`src/tools/repo_scanner.py`

职责：

- 接收项目路径。
- 递归扫描 Python 文件。
- 忽略 `.git`、虚拟环境、缓存目录。
- 区分源码文件和测试文件。
- 返回结构化扫描结果。

### 3.2 Local Executor

位置：`src/sandbox/local_executor.py`

职责：

- 使用 `python -m pytest` 执行目标项目测试。
- 设置超时时间。
- 捕获 stdout、stderr、退出码和耗时。
- 返回结构化执行结果。

第一阶段命名为 `sandbox` 是为了保持模块边界稳定。第二阶段已加入 `docker_executor.py`，实现 Docker 权限隔离。

### 3.3 Docker Executor

位置：`src/sandbox/docker_executor.py`

职责：

- 使用 `docker run` 在容器中执行 pytest。
- 将目标项目只读挂载到 `/workspace`。
- 禁用网络并限制 CPU、内存、进程数和执行时间。
- 返回与本地执行器一致的结构化执行结果。

### 3.4 Sandbox Policy

位置：`src/sandbox/policy.py`

职责：

- 集中描述 Docker 沙箱策略。
- 管理镜像名、网络开关、挂载模式、资源限制和超时时间。

### 3.5 Workflow Pipeline

位置：`src/workflow/pipeline.py`

职责：

- 编排项目扫描与测试执行。
- 将扫描结果和执行结果合并为报告对象。
- 为后续 LangGraph 工作流提供替换点。

### 3.6 Test Planner Agent

位置：`src/agents/test_planner.py`

职责：

- 使用 Python AST 分析源码文件中的公开函数。
- 为每个函数生成结构化测试场景。
- 记录测试设计理由，使生成过程可解释、可评估。
- 为规则型或 LLM 测试生成器提供输入。

### 3.7 Test Generator Agent

位置：`src/agents/test_generator.py`

职责：

- 使用 Python AST 分析源码文件中的公开函数。
- 根据 TestPlan 中的测试场景生成基础 pytest 测试。
- 对生成测试执行 AST 安全校验，阻止危险 import。
- 返回生成测试文件内容和覆盖函数列表。

当前实现为规则型生成器，后续可替换为 LLM Test Generator Agent。

### 3.8 Test Workspace

### 3.8 Security Checker Agent

位置：`src/agents/security_checker.py`

职责：

- 使用 Python AST 检查生成测试代码。
- 拦截危险 import，如 `subprocess`、`socket`、`requests`。
- 拦截高风险调用，如 `eval`、`exec`、`open`。
- 输出结构化 SecurityCheckResult，进入 CLI 和 JSON 报告。

### 3.9 Test Workspace

位置：`src/tools/test_workspace.py`

职责：

- 将目标项目复制到临时工作区。
- 写入生成的测试文件。
- 让本地执行器或 Docker 执行器在临时副本中运行测试，避免修改原始项目。

### 3.10 Result Analyzer Agent

位置：`src/agents/result_analyzer.py`

职责：

- 解析 pytest stdout / stderr 中的汇总行。
- 提取 passed、failed、errors、skipped、warnings 和 total。
- 根据执行结果生成 conclusion，如 `passed`、`failed`、`timeout` 或 `execution_error`。

### 3.11 Failure Diagnoser Agent

位置：`src/agents/failure_diagnoser.py`

职责：

- 根据 pytest 输出和 PytestSummary 判断失败类型。
- 提取 FAILED / ERROR 目标和关键错误行。
- 为 assertion failure、import error、timeout 等常见问题生成修复建议。

### 3.12 Report Writer

位置：`src/tools/report_writer.py`

职责：

- 将 PipelineReport 转换为 JSON 结构。
- 写出可审计、可复现的运行报告。
- 支持最终报告中的测试评估证据留存。

### 3.13 Benchmark Evaluator

位置：`src/evaluation/benchmark.py`

职责：

- 定义 BenchmarkCase 和 BenchmarkResult。
- 批量运行 pipeline。
- 聚合通过率、pytest 用例数量、规划测试数量、生成测试数量和总耗时。
- 写出 Benchmark JSON 报告。

### 3.14 Future Agent Modules

### 3.14 LLM Prompt Builder

位置：`src/llm/prompt_builder.py`

职责：

- 根据 TestPlan 和源码上下文构造 LLM 测试生成 Prompt。
- 在 system prompt 中写入安全约束。
- 控制源码上下文长度，避免 Prompt 过大。
- 支持后续接入 DashScope、DeepSeek、OpenAI 或 Ollama。

### 3.15 LLM Config

位置：`src/llm/config.py`

职责：

- 从环境变量读取 LLM provider、model 和 API Key 是否存在。
- 只记录 `api_key_set` 布尔值，不写出 API Key 明文。

### 3.16 Code Reviewer Agent

位置：`src/agents/code_reviewer.py`

职责：

- 使用 Python AST 审查源码文件。
- 发现危险调用，如 `eval`、`exec`、`__import__` 和 `subprocess.*`。
- 发现疑似硬编码密钥、宽泛异常处理、缺失测试覆盖和除零边界风险。
- 输出 `ReviewFinding` 列表，供 CLI 和 JSON 报告消费。

### 3.17 Future Agent Modules

位置：`src/agents/`

当前已实现规则型 Test Generator Agent。后续计划：

- Repo Analyzer Agent：理解项目结构和核心模块。
- Test Planner Agent：生成测试计划。
- LLM Test Generator Agent：基于规格和源码上下文生成 pytest 测试代码。
- Result Analyzer Agent：分析失败原因并生成修复建议。

## 4. 权限隔离设计

Docker 沙箱执行器采用以下策略：

- 源码目录只读挂载。
- 生成测试目录单独可写。
- 禁用网络：`--network none`。
- 限制 CPU：`--cpus 1`。
- 限制内存：`--memory 512m`。
- 限制进程数：`--pids-limit 128`。
- 限制执行时间：由宿主进程 timeout 控制。
- 使用临时目录承载执行产物，测试完成后清理。

## 5. 数据流

```text
Project Path
  -> RepositoryScanResult
  -> TestPlan
  -> GeneratedTestSuite
  -> SecurityCheckResult
  -> Temporary Workspace
  -> TestExecutionResult
  -> PytestSummary
  -> FailureDiagnosis
  -> PipelineReport
  -> CLI Output / JSON Trace

Benchmark Data Flow:

BenchmarkCase
  -> PipelineReport
  -> BenchmarkSummary
  -> Benchmark JSON Report

LLM Prompt Flow:

TestPlan
  -> Source Context
  -> LLMTestPrompt
  -> Prompt JSON Artifact

Code Review Flow:

RepositoryScanResult
  -> Code Reviewer Agent
  -> ReviewReport
  -> Review JSON Artifact
```

## 6. 可观测性

当前记录：

- 源码文件数量。
- 测试文件数量。
- pytest 退出码。
- stdout / stderr。
- 执行耗时。
- 是否超时。
- pytest 汇总统计。
- 生成测试安全检查结果。
- 失败诊断与修复建议。
- JSON 运行报告。
- LLM Prompt JSON 工件。
- Benchmark 汇总指标。
- Code Review JSON 工件。

后续将扩展为：

- Agent trace。
- LLM prompt / response 摘要。
- 覆盖率数据。
- Benchmark 数据集评估结果。
