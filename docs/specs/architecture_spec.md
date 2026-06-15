# Architecture Spec: TestGuard Agent

## 1. 架构目标

TestGuard Agent 采用分层架构，将代码理解、测试规划、测试生成、隔离执行和结果分析解耦。第一阶段实现仓库扫描与本地测试执行，第二阶段加入 Docker 沙箱执行器。

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

### 3.6 Agent Modules

位置：`src/agents/`

第一阶段仅保留模块边界。后续计划：

- Repo Analyzer Agent：理解项目结构和核心模块。
- Test Planner Agent：生成测试计划。
- Test Generator Agent：生成 pytest 测试代码。
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
  -> TestExecutionResult
  -> PipelineReport
  -> CLI Output / Future JSON Trace
```

## 6. 可观测性

第一阶段记录：

- 源码文件数量。
- 测试文件数量。
- pytest 退出码。
- stdout / stderr。
- 执行耗时。
- 是否超时。

后续将扩展为：

- Agent trace。
- LLM prompt / response 摘要。
- 覆盖率数据。
- Benchmark 数据集评估结果。
