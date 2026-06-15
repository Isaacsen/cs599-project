# API Spec: TestGuard Agent

## 1. 命令行 API

### 1.1 执行测试闭环

```bash
python -m src.main <project_path> [--timeout SECONDS] [--executor local|docker] [--docker-image IMAGE]
```

参数：

- `project_path`：待扫描和测试的 Python 项目路径。
- `--timeout`：测试执行超时时间，默认 30 秒。
- `--executor`：测试执行后端，默认 `local`，可选 `docker`。
- `--docker-image`：Docker 执行后端使用的镜像，默认 `testguard-python:latest`。

示例：

```bash
python -m src.main examples/sample_python_project --timeout 30
```

Docker 沙箱执行示例：

```bash
docker build -f Dockerfile.sandbox -t testguard-python .
python -m src.main examples/sample_python_project --executor docker
```

输出：

```text
[TestGuard Agent MVP]

Project: examples/sample_python_project
Language: Python
Test Framework: pytest
Source files: 1
Test files: 1
Test Result: PASSED
Executor: docker
Duration: 0.50s
```

## 2. 内部数据结构

### 2.1 RepositoryScanResult

字段：

- `project_path: str`
- `language: str`
- `test_framework: str`
- `source_files: list[str]`
- `test_files: list[str]`

### 2.2 TestExecutionResult

字段：

- `passed: bool`
- `exit_code: int | None`
- `stdout: str`
- `stderr: str`
- `duration_seconds: float`
- `timed_out: bool`
- `executor: str`

### 2.3 PipelineReport

字段：

- `scan: RepositoryScanResult`
- `execution: TestExecutionResult`

## 3. 后续 HTTP API 规划

后续如果加入 FastAPI 服务，计划提供：

- `POST /runs`：创建一次测试生成与执行任务。
- `GET /runs/{run_id}`：查询任务状态和报告。
- `GET /runs/{run_id}/trace`：查看 Agent 运行轨迹。

第一阶段优先保证命令行闭环稳定运行。
