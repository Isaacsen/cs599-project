# Architecture Spec: Software Engineer Agent

## 1. 架构目标

Software Engineer Agent 采用分层架构，将代码理解、代码审查、LLM 语义审查、自动修 Bug、Patch 审查、单测生成、LLM 测试生成、隔离执行、修复循环、覆盖反馈和报告输出解耦。当前主架构已经迁移为基于 LangGraph `StateGraph` 的软件工程师 Agent；早期的测试生成 Pipeline、Benchmark、独立 review/fix/unit_tests/llm_tests CLI 保留为辅助入口和可复现评估工件。

## 2. 总体流程

```text
Repo Scanner
  -> Rule Code Reviewer Agent
  -> LLM Code Reviewer Agent
  -> Bug Fixer Agent
  -> Patch Reviewer Agent
  -> Unit Test Writer Agent
  -> LLM Test Generator Agent
  -> Sandbox Validator Agent
  -> Repair Loop Agent
  -> Coverage Feedback Agent
  -> Software Engineer Report Writer
```

推荐演示命令默认启用真实 LLM 节点和 Docker 沙箱节点。CLI 保留独立开关，便于在无模型或无 Docker 的环境下运行精简流。

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

第十阶段自动修 Bug 流程：

```text
Repo Scanner
  -> Bug Fixer Agent
  -> Fix Plan Writer
  -> Optional Source Apply
```

第十一阶段缺失覆盖单测生成流程：

```text
Repo Scanner
  -> Unit Test Writer Agent
  -> Security Checker
  -> Unit Test Report Writer
  -> Optional Test File Apply
```

当前软件工程师 Agent 主流程：

```text
Repo Scanner
  -> Code Reviewer Agent
  -> LLM Code Reviewer Agent
  -> Bug Fixer Agent
  -> Patch Reviewer Agent
  -> Unit Test Writer Agent
  -> LLM Prompt Builder
  -> OpenAI-compatible LLM Client
  -> Security Checker
  -> Sandbox Validator Agent
  -> Repair Loop Agent
  -> Coverage Feedback Agent
  -> Software Engineer JSON / Markdown Report
```

第十三阶段 LLM 测试生成流程仍可通过 `src.llm_tests` 独立运行，作为主流程中 `llm_tests` 节点的辅助入口。

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

当前保留规则型生成器作为稳定离线兜底，同时提供 LLM Test Generator Agent 作为可插拔增强路径。

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

### 3.14 LLM Prompt Builder

位置：`src/llm/prompt_builder.py`

职责：

- 根据 TestPlan 和源码上下文构造 LLM 测试生成 Prompt。
- 在 system prompt 中写入安全约束。
- 控制源码上下文长度，避免 Prompt 过大。
- 支持接入 DashScope、DeepSeek、OpenAI 或 Ollama。

### 3.15 LLM Config

位置：`src/llm/config.py`

职责：

- 从环境变量读取 LLM provider、model 和 API Key 是否存在。
- 只记录 `api_key_set` 布尔值，不写出 API Key 明文。
- 支持 `LLM_BASE_URL` 覆盖 OpenAI-compatible 网关地址。

### 3.16 LLM Client

位置：`src/llm/client.py`

职责：

- 使用标准库调用 OpenAI-compatible Chat Completions 接口。
- 默认支持 DashScope、DeepSeek、OpenAI 和 Ollama 风格 base URL。
- 仅在请求头中使用 API Key，不写出 API Key 明文。
- 通过环境变量读取 DashScope、DeepSeek、OpenAI-compatible 或 Ollama 配置并执行真实 LLM 调用。

### 3.17 Code Reviewer Agent

位置：`src/agents/code_reviewer.py`

职责：

- 使用 Python AST 审查源码文件。
- 发现危险调用，如 `eval`、`exec`、`__import__` 和 `subprocess.*`。
- 发现疑似硬编码密钥、宽泛异常处理、缺失测试覆盖和除零边界风险。
- 输出 `ReviewFinding` 列表，供 CLI 和 JSON 报告消费。

### 3.18 Bug Fixer Agent

位置：`src/agents/bug_fixer.py`

职责：

- 使用 AST 与行级变换生成安全修复计划。
- 默认 dry-run，输出 `FixPlan`，不修改目标源码。
- 在用户显式启用 `--apply` 时写回目标文件。
- 当前支持 `eval` 替换、疑似密钥环境变量化、宽泛异常收窄和除零保护。

### 3.19 Unit Test Writer Agent

位置：`src/agents/unit_test_writer.py`

职责：

- 复用 Test Planner 和 Test Generator 生成 pytest 内容。
- 对比现有测试文本，跳过已覆盖的公开函数。
- 复用 Security Checker 校验生成测试代码。
- 默认 dry-run 输出 JSON 报告，`--apply` 时写入目标项目测试文件。

### 3.20 Software Engineer Agent

位置：

- `src/workflow/software_engineer_graph.py`
- `src/engineer.py`
- `src/engineer_graph.py`
- `src/tools/software_engineer_graph_writer.py`

职责：

- 使用 LangGraph `StateGraph` 编排扫描、规则代码审查、LLM 代码审查、自动修 Bug 计划、Patch 审查、缺失覆盖单测生成、LLM 测试生成、沙箱验证、修复循环和覆盖反馈。
- 保持默认 dry-run，避免未经确认修改用户项目。
- 将 `ReviewReport`、`LLMCodeReviewReport`、`FixPlan`、`PatchReviewReport`、`UnitTestReport`、`LLMTestGenerationReport`、`SandboxValidationReport`、`RepairLoopReport` 和 `CoverageFeedbackReport` 汇总为统一报告。
- 记录 `node_trace`、`graph_runtime` 和 `status`，用于演示 Agent 状态流转。
- 为课程演示提供一个完整的软件工程师 Agent 入口。

### 3.21 LLM Test Generator Agent

位置：`src/agents/llm_test_generator.py`

职责：

- 基于 TestPlan 和源码上下文构造 LLM Prompt。
- 调用真实 LLM Client 获取 pytest 代码。
- 从模型响应中提取 Python 代码块。
- 使用 Security Checker 校验生成测试。
- 输出 `LLMTestGenerationReport`，支持 dry-run 和可选写入测试文件。

### 3.22 LLM Code Reviewer Agent

位置：`src/agents/llm_code_reviewer.py`

职责：

- 基于仓库扫描结果构造审查 Prompt。
- 调用真实 OpenAI-compatible LLM Client 进行语义代码审查。
- 将模型输出归一化为 `LLMCodeReviewReport`，只记录 provider、model 和 API Key 是否存在，不写出密钥明文。

### 3.23 Patch Reviewer Agent

位置：`src/agents/patch_reviewer.py`

职责：

- 消费 `FixPlan`。
- 检查修复计划是否仍包含高风险模式。
- 输出 `PatchReviewReport`，为后续沙箱验证和修复循环提供门禁信号。

### 3.24 Sandbox Validator Agent

位置：`src/agents/sandbox_validator.py`

职责：

- 将规则生成测试和 LLM 生成测试写入临时工作区。
- 调用本地或 Docker 沙箱执行 pytest。
- 复用结果分析与失败诊断，输出 `SandboxValidationReport`。

### 3.25 Repair Loop Agent

位置：`src/agents/repair_loop.py`

职责：

- 根据 Patch 审查和沙箱验证结果规划下一轮修复动作。
- 记录迭代预算、下一步状态和建议动作。
- 当前以计划模式运行，不自动无限写回源码。

### 3.26 Coverage Feedback Agent

位置：`src/agents/coverage_feedback.py`

职责：

- 汇总规则单测与 LLM 单测覆盖的公开函数。
- 输出覆盖比例、已覆盖函数和缺失函数。
- 为下一轮测试生成提供反馈。

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

Bug Fix Flow:

RepositoryScanResult
  -> Bug Fixer Agent
  -> FixPlan
  -> Fix Plan JSON Artifact
  -> Optional Source Apply

Unit Test Writer Flow:

RepositoryScanResult
  -> Existing Test Text
  -> Unit Test Writer Agent
  -> SecurityCheckResult
  -> Unit Test JSON Artifact
  -> Optional Test File Apply

Software Engineer LangGraph Flow:

RepositoryScanResult
  -> StateGraph scan node
  -> StateGraph review node
  -> ReviewReport
  -> StateGraph llm_review node
  -> LLMCodeReviewReport
  -> StateGraph fix node
  -> FixPlan
  -> StateGraph patch_review node
  -> PatchReviewReport
  -> StateGraph unit_tests node
  -> UnitTestReport
  -> StateGraph llm_tests node
  -> LLMTestGenerationReport
  -> StateGraph sandbox_validate node
  -> SandboxValidationReport
  -> StateGraph repair_loop node
  -> RepairLoopReport
  -> StateGraph coverage_feedback node
  -> CoverageFeedbackReport
  -> Node Trace
  -> Software Engineer JSON / Markdown Artifact

LLM Test Generation Flow:

RepositoryScanResult
  -> TestPlan
  -> LLMTestPrompt
  -> LLM Client
  -> SecurityCheckResult
  -> LLM Test JSON Artifact
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
- Bug Fix Plan JSON 工件。
- Unit Test Writer JSON 工件。
- Software Engineer JSON 工件。
- Software Engineer Markdown 工件。
- LLM Test JSON 工件。
- LLM 代码审查摘要。
- Patch 审查结果。
- 沙箱验证结果。
- 修复循环计划。
- 覆盖反馈结果。

进一步增强方向：

- 更大规模 Benchmark 数据集评估结果。
- Codebase RAG 检索证据。
- 更细粒度的容器 seccomp / AppArmor 配置。
