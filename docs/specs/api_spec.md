# API Spec: TestGuard Agent

## 1. 命令行 API

### 1.1 执行测试闭环

```bash
python -m src.main <project_path> [--timeout SECONDS] [--executor local|docker] [--docker-image IMAGE] [--generate-tests] [--report-json PATH]
```

参数：

- `project_path`：待扫描和测试的 Python 项目路径。
- `--timeout`：测试执行超时时间，默认 30 秒。
- `--executor`：测试执行后端，默认 `local`，可选 `docker`。
- `--docker-image`：Docker 执行后端使用的镜像，默认 `testguard-python:latest`。
- `--generate-tests`：执行前生成 pytest 测试，并在临时项目副本中运行。
- `--report-json`：可选 JSON 报告输出路径。

示例：

```bash
python -m src.main examples/sample_python_project --timeout 30
```

Docker 沙箱执行示例：

```bash
docker build -f Dockerfile.sandbox -t testguard-python .
python -m src.main examples/sample_python_project --executor docker
```

生成测试并使用 Docker 沙箱执行：

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker
```

生成测试、沙箱执行并保存 JSON 报告：

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker --report-json docs/runs/sample_run.json
```

输出：

```text
[TestGuard Agent MVP]

Project: examples/sample_python_project
Language: Python
Test Framework: pytest
Source files: 1
Test files: 1
Generated Tests: True
Planned Test Cases: 2
Generated Test Cases: 2
Security Check: passed
Test Result: PASSED
Executor: docker
Duration: 0.50s
Pytest Summary:
  total: 5
  passed: 5
  failed: 0
  errors: 0
  skipped: 0
  warnings: 0
  conclusion: passed
Diagnosis:
  status: no_issue
  failure_types: none
```

### 1.2 执行 Benchmark 评估

```bash
python -m src.benchmark [--case name=project_path] [--timeout SECONDS] [--executor local|docker] [--docker-image IMAGE] [--output PATH]
```

参数：

- `--case`：可选 Benchmark 用例，格式为 `name=project_path`，可重复传入。
- `--timeout`：每个用例的测试执行超时时间，默认 30 秒。
- `--executor`：测试执行后端，默认 `local`，可选 `docker`。
- `--docker-image`：Docker 执行后端使用的镜像，默认 `testguard-python:latest`。
- `--output`：Benchmark JSON 输出路径，默认 `docs/runs/benchmark.json`。

示例：

```bash
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

输出：

```text
[TestGuard Benchmark]

Total Cases: 1
Passed Cases: 1
Failed Cases: 0
Pass Rate: 100.00%
Total Pytest Cases: 5
Planned Test Cases: 2
Generated Test Cases: 2
Total Duration: 1.00s
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
- `generated_suite: GeneratedTestSuite | None`
- `generated_tests_enabled: bool`
- `analysis: PytestSummary`
- `test_plan: TestPlan | None`
- `diagnosis: FailureDiagnosis`
- `security_check: SecurityCheckResult | None`

### 2.4 GeneratedTestSuite

字段：

- `test_file_name: str`
- `content: str`
- `covered_functions: list[str]`

### 2.5 PytestSummary

字段：

- `passed: int`
- `failed: int`
- `errors: int`
- `skipped: int`
- `warnings: int`
- `total: int`
- `conclusion: str`

### 2.6 TestPlan

字段：

- `items: list[TestPlanItem]`

### 2.7 TestPlanItem

字段：

- `module_name: str`
- `function_name: str`
- `scenario: str`
- `rationale: str`

### 2.8 BenchmarkSummary

字段：

- `total_cases: int`
- `passed_cases: int`
- `failed_cases: int`
- `pass_rate: float`
- `total_pytest_cases: int`
- `generated_test_cases: int`
- `planned_test_cases: int`
- `total_duration_seconds: float`

### 2.9 FailureDiagnosis

字段：

- `status: str`
- `failure_types: list[str]`
- `key_findings: list[str]`
- `suggestions: list[str]`

### 2.10 SecurityCheckResult

字段：

- `passed: bool`
- `violations: list[SecurityViolation]`

### 2.11 SecurityViolation

字段：

- `rule: str`
- `detail: str`
- `line: int`

## 3. 后续 HTTP API 规划

后续如果加入 FastAPI 服务，计划提供：

- `POST /runs`：创建一次测试生成与执行任务。
- `GET /runs/{run_id}`：查询任务状态和报告。
- `GET /runs/{run_id}/trace`：查看 Agent 运行轨迹。

第一阶段优先保证命令行闭环稳定运行。
