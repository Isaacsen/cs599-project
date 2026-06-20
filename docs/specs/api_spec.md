# API Spec: TestGuard Agent

## 1. 命令行 API

### 1.1 执行测试闭环

```bash
python -m src.main <project_path> [--timeout SECONDS] [--executor local|docker] [--docker-image IMAGE] [--generate-tests] [--report-json PATH] [--export-llm-prompt PATH]
```

参数：

- `project_path`：待扫描和测试的 Python 项目路径。
- `--timeout`：测试执行超时时间，默认 30 秒。
- `--executor`：测试执行后端，默认 `local`，可选 `docker`。
- `--docker-image`：Docker 执行后端使用的镜像，默认 `testguard-python:latest`。
- `--generate-tests`：执行前生成 pytest 测试，并在临时项目副本中运行。
- `--report-json`：可选 JSON 报告输出路径。
- `--export-llm-prompt`：可选 LLM 测试生成 Prompt 输出路径，需要配合 `--generate-tests` 使用。

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

导出 LLM Prompt：

```bash
python -m src.main examples/sample_python_project --generate-tests --export-llm-prompt docs/runs/llm_prompt.json
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

### 1.3 执行代码审查

```bash
python -m src.review <project_path> [--output PATH]
```

参数：

- `project_path`：待审查的 Python 项目路径。
- `--output`：代码审查 JSON 输出路径，默认 `docs/runs/review.json`。

示例：

```bash
python -m src.review examples/review_target --output docs/runs/review.json
```

输出：

```text
[TestGuard Code Review]

Project: examples/review_target
Findings: 7
High: 2
Medium: 5
Low: 0
```

### 1.4 生成自动修 Bug 计划

```bash
python -m src.fix <project_path> [--output PATH] [--apply]
```

参数：

- `project_path`：待分析或修复的 Python 项目路径。
- `--output`：修复计划 JSON 输出路径，默认 `docs/runs/fix_plan.json`。
- `--apply`：可选开关，启用后将安全修复写回目标项目；不传入时只生成 dry-run 计划。

示例：

```bash
python -m src.fix examples/review_target --output docs/runs/fix_plan.json
```

输出：

```text
[TestGuard Bug Fix]

Project: examples/review_target
Applied: False
Edits: 6
Files Changed: 1
```

### 1.5 生成缺失覆盖单元测试

```bash
python -m src.unit_tests <project_path> [--output PATH] [--test-file PATH] [--max-functions N] [--apply]
```

参数：

- `project_path`：待分析的 Python 项目路径。
- `--output`：单测生成 JSON 输出路径，默认 `docs/runs/unit_tests.json`。
- `--test-file`：启用 `--apply` 时写入的项目内测试文件路径，默认 `tests/test_testguard_generated.py`。
- `--max-functions`：最多考虑的公开函数数量，默认 8。
- `--apply`：可选开关，启用后将生成的 pytest 文件写入目标项目；不传入时只生成 dry-run 报告。

示例：

```bash
python -m src.unit_tests examples/review_target --output docs/runs/unit_tests.json
```

输出：

```text
[TestGuard Unit Test Writer]

Project: examples/review_target
Applied: False
Test File: tests/test_testguard_generated.py
Planned Test Cases: 3
Generated Test Cases: 3
Security Check: passed
```

### 1.6 运行软件工程师 Agent

```bash
python -m src.engineer <project_path> [--output PATH] [--apply-fixes] [--apply-tests] [--use-llm-tests] [--mock-llm-response PATH] [--test-file PATH] [--llm-test-file PATH] [--max-functions N]
```

参数：

- `project_path`：待分析的 Python 项目路径。
- `--output`：统一软件工程师报告输出路径，默认 `docs/runs/software_engineer.json`。
- `--apply-fixes`：可选开关，启用后应用安全修复。
- `--apply-tests`：可选开关，启用后写入生成的 pytest 测试。
- `--use-llm-tests`：可选开关，启用后在 LangGraph 工作流中追加 LLM 测试生成节点。
- `--mock-llm-response`：可选离线 mock response 文件，用于课程演示和无网络测试。
- `--test-file`：启用 `--apply-tests` 时写入的项目内测试文件路径，默认 `tests/test_testguard_generated.py`。
- `--llm-test-file`：启用 `--apply-tests` 时写入的 LLM 生成测试文件路径，默认 `tests/test_testguard_llm_generated.py`。
- `--max-functions`：最多考虑的公开函数数量，默认 8。

示例：

```bash
python -m src.engineer examples/review_target --use-llm-tests --mock-llm-response examples/llm_response/review_target_response.md --output docs/runs/software_engineer.json
```

输出：

```text
[TestGuard Software Engineer LangGraph]

Project: examples/review_target
Status: completed
Runtime: langgraph
Node Trace: scan -> review -> fix -> unit_tests -> llm_tests -> finish

Review Findings: 7
Fix Edits: 6
Generated Unit Tests: 3
Generated LLM Tests: 3
```

### 1.7 运行 LLM 测试生成 Agent

```bash
python -m src.llm_tests <project_path> [--output PATH] [--test-file PATH] [--max-functions N] [--mock-response PATH] [--apply]
```

参数：

- `project_path`：待分析的 Python 项目路径。
- `--output`：LLM 测试生成 JSON 输出路径，默认 `docs/runs/llm_tests.json`。
- `--test-file`：启用 `--apply` 时写入的项目内测试文件路径，默认 `tests/test_testguard_llm_generated.py`。
- `--max-functions`：最多考虑的公开函数数量，默认 8。
- `--mock-response`：可选离线 mock response 文件，用于无网络或无 API Key 的演示。
- `--apply`：可选开关，启用后将 LLM 生成的 pytest 文件写入目标项目；不传入时只生成 dry-run 报告。

示例：

```bash
python -m src.llm_tests examples/sample_python_project --mock-response examples/llm_response/pytest_response.md --output docs/runs/llm_tests.json
```

输出：

```text
[TestGuard LLM Test Generator]

Project: examples/sample_python_project
Status: generated
Provider: dashscope
Model: glm-5.2
Generated Test Cases: 2
Security Check: passed
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

### 2.12 LLMTestPrompt

字段：

- `system: str`
- `user: str`
- `covered_functions: list[str]`

### 2.13 ReviewReport

字段：

- `project_path: str`
- `findings: list[ReviewFinding]`

派生统计：

- `finding_count: int`
- `high_count: int`
- `medium_count: int`
- `low_count: int`

### 2.14 ReviewFinding

字段：

- `file_path: str`
- `line: int`
- `severity: str`
- `rule: str`
- `message: str`
- `suggestion: str`

### 2.15 FixPlan

字段：

- `project_path: str`
- `applied: bool`
- `edits: list[FixEdit]`

派生统计：

- `edit_count: int`
- `files_changed: int`

### 2.16 FixEdit

字段：

- `file_path: str`
- `line: int`
- `rule: str`
- `description: str`
- `before: str`
- `after: str`

### 2.17 UnitTestReport

字段：

- `project_path: str`
- `applied: bool`
- `test_file_path: str`
- `test_plan: TestPlan`
- `suite: GeneratedTestSuite`
- `security_check: SecurityCheckResult`

派生统计：

- `planned_test_count: int`
- `generated_test_count: int`

### 2.18 SoftwareEngineerGraphState

字段：

- `project_path: str`
- `apply_fixes: bool`
- `apply_tests: bool`
- `use_llm_tests: bool`
- `scan: RepositoryScanResult`
- `review: ReviewReport`
- `fix_plan: FixPlan`
- `unit_tests: UnitTestReport`
- `llm_tests: LLMTestGenerationReport | None`
- `node_trace: list[str]`
- `graph_runtime: str`
- `status: str`

### 2.19 SoftwareEngineerGraphResult

字段：

- `project_path: str`
- `state: SoftwareEngineerGraphState`

派生统计：

- `finding_count: int`
- `fix_edit_count: int`
- `generated_unit_test_count: int`
- `generated_llm_test_count: int`
- `node_trace: list[str]`

### 2.20 LLMTestGenerationReport

字段：

- `project_path: str`
- `status: str`
- `applied: bool`
- `provider: str`
- `model: str`
- `api_key_set: bool`
- `api_key_env: str`
- `test_file_path: str`
- `prompt: LLMTestPrompt`
- `test_plan: TestPlan`
- `suite: GeneratedTestSuite | None`
- `security_check: SecurityCheckResult | None`

派生统计：

- `generated_test_count: int`

## 3. 后续 HTTP API 规划

后续如果加入 FastAPI 服务，计划提供：

- `POST /runs`：创建一次测试生成与执行任务。
- `GET /runs/{run_id}`：查询任务状态和报告。
- `GET /runs/{run_id}/trace`：查看 Agent 运行轨迹。

第一阶段优先保证命令行闭环稳定运行。
