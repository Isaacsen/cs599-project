# TestGuard Software Engineer Agent Architecture

## 1. 新项目定位

TestGuard 当前定位为 **面向 Python 项目的软件工程师 Agent 与权限隔离执行平台**。

系统不再只是“自动生成测试并执行”的单一工具，而是围绕软件工程师日常工作流进行 Agent 化编排：

- 代码审查：发现危险调用、疑似硬编码密钥、宽泛异常、测试缺失和边界风险。
- 自动修 Bug：默认 dry-run 生成修复计划，用户确认后才写回。
- 生成单测：为缺失覆盖的公开函数生成 pytest。
- LLM 测试生成：接入 DashScope / DeepSeek / OpenAI-compatible 模型，离线 mock 可兜底演示。
- 权限隔离执行：通过 Docker 沙箱、临时工作区、只读挂载、禁用网络和资源限制降低执行风险。

该设计对应课程方向一“Agentic AI 原生开发”，覆盖 SDD、工具调用、状态管理、多步骤推理、可观测性与评估、Docker 沙箱等课程要求。

## 2. 总体架构

```mermaid
flowchart TD
    U["用户 / Demo CLI"] --> CLI["CLI 入口层"]

    CLI --> SE["Software Engineer Agent"]
    CLI --> TG["TestGuard Pipeline"]
    CLI --> LLMG["LLM Test Generator Agent"]
    CLI --> BM["Benchmark Evaluator"]

    SE --> CR["Code Reviewer Agent"]
    SE --> BF["Bug Fixer Agent"]
    SE --> UT["Unit Test Writer Agent"]

    TG --> RP["Repo Scanner"]
    TG --> TP["Test Planner Agent"]
    TG --> RTG["Rule-based Test Generator Agent"]
    TG --> SC["Security Checker Agent"]
    TG --> WS["Temporary Test Workspace"]
    TG --> SX["Sandbox Executor"]
    TG --> RA["Result Analyzer Agent"]
    TG --> FD["Failure Diagnoser Agent"]

    LLMG --> TP
    LLMG --> PB["LLM Prompt Builder"]
    LLMG --> LC["OpenAI-compatible LLM Client"]
    LLMG --> SC

    CR --> RP
    BF --> RP
    UT --> RP
    UT --> TP
    UT --> SC

    SX --> LE["Local Executor"]
    SX --> DE["Docker Executor"]
    DE --> ISO["Permission Isolation Layer"]

    ISO --> I1["Read-only source mount"]
    ISO --> I2["Network disabled"]
    ISO --> I3["CPU / Memory / PID limits"]
    ISO --> I4["Timeout control"]
    ISO --> I5["No new privileges"]

    CR --> OBS["JSON Artifacts / Observability"]
    BF --> OBS
    UT --> OBS
    LLMG --> OBS
    RA --> OBS
    FD --> OBS
    BM --> OBS
```

## 3. 分层设计

### 3.1 CLI 入口层

面向课程 Demo 和评审者，提供可重复运行的命令：

- `src.main`：测试生成、沙箱执行、结果分析主闭环。
- `src.review`：代码审查。
- `src.fix`：自动修 Bug 计划。
- `src.unit_tests`：缺失覆盖单测生成。
- `src.engineer`：默认 LangGraph 软件工程师 Agent。
- `src.engineer_graph`：显式 LangGraph 软件工程师 Agent 入口。
- `src.llm_tests`：LLM 测试生成。
- `src.benchmark`：评估与指标汇总。

### 3.2 Agent 编排层

核心是基于 LangGraph `StateGraph` 的 `Software Engineer Agent`：

```text
scan
  -> review
  -> fix
  -> unit_tests
  -> optional llm_tests
  -> finish
  -> SoftwareEngineerGraphResult
```

该层体现 Agentic AI 的多步骤推理与状态管理。每个节点都消费并返回结构化状态，最终合并为统一 JSON 报告，并记录 `node_trace`、`status` 和 `graph_runtime`。

### 3.3 工具调用层

系统中的工具均保持小而明确的边界：

- `repo_scanner`：扫描 Python 项目。
- `test_workspace`：创建临时测试工作区。
- `report_writer` / `review_writer` / `fix_writer` / `unit_test_writer` / `llm_test_writer`：输出结构化工件。
- `prompt_builder`：将 TestPlan 和源码上下文转为 LLM Prompt。
- `llm.client`：通过 OpenAI-compatible 接口调用 DashScope、DeepSeek 等模型。

这些模块可视为 Function Calling / Tool Use 的本地实现。

### 3.4 权限隔离层

权限隔离由三道闸组成：

1. 生成代码执行前必须经过 Security Checker。
2. 默认 dry-run，不直接写回用户项目；写回必须显式传入 `--apply` / `--apply-fixes` / `--apply-tests`。
3. 测试执行可进入 Docker 沙箱，限制网络、文件系统和资源。

```mermaid
flowchart LR
    A["Generated / LLM Code"] --> B["Security Checker"]
    B --> C{"Passed?"}
    C -->|No| D["Block and report violations"]
    C -->|Yes| E["Temporary Workspace"]
    E --> F["Docker Sandbox"]
    F --> G["Read-only source + no network + resource limits"]
    G --> H["Pytest Result"]
```

### 3.5 可观测与评估层

所有关键 Agent 都输出 JSON 工件：

- `sample_run.json`
- `benchmark.json`
- `llm_prompt.json`
- `llm_tests.json`
- `review.json`
- `fix_plan.json`
- `unit_tests.json`
- `software_engineer.json`
- `software_engineer_graph.json`

这些工件支持课程报告中的测试评估、Demo 兜底和可复现审计。

## 4. 数据流

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant SE as Software Engineer Agent
    participant Review as Code Reviewer
    participant Fix as Bug Fixer
    participant Unit as Unit Test Writer
    participant LLM as LLM Test Generator
    participant Sandbox as Sandbox Executor
    participant Obs as JSON Artifacts

    User->>CLI: python -m src.engineer project --use-llm-tests
    CLI->>SE: run LangGraph dry-run workflow
    SE->>Review: analyze repository
    Review-->>SE: ReviewReport
    SE->>Fix: generate safe fix plan
    Fix-->>SE: FixPlan
    SE->>Unit: generate missing unit tests
    Unit-->>SE: UnitTestReport
    SE->>LLM: optional LLM test node
    LLM-->>SE: LLMTestGenerationReport
    SE-->>Obs: software_engineer.json

    User->>CLI: python -m src.llm_tests project
    CLI->>LLM: build prompt + call LLM/mock
    LLM-->>Obs: llm_tests.json

    User->>CLI: python -m src.main --generate-tests --executor docker
    CLI->>Sandbox: execute generated tests
    Sandbox-->>Obs: sample_run.json
```

## 5. 课程要求映射

| 课程要求 | 架构对应 |
| --- | --- |
| SDD 规格驱动开发 | `docs/specs/product_spec.md`、`architecture_spec.md`、`api_spec.md` |
| 工具使用 / Function Calling | Repo Scanner、Security Checker、Docker Executor、LLM Client、Report Writers |
| 状态管理与多步骤推理 | LangGraph StateGraph 串联 scan/review/fix/unit_tests/llm_tests/finish 节点 |
| 多智能体协作 | Code Reviewer、Bug Fixer、Unit Test Writer、LLM Test Generator 分工协作 |
| 可观测性与评估 | JSON artifacts、Benchmark、单元测试、Demo Guide |
| 权限隔离 | Docker 沙箱、Security Checker、dry-run apply gate、环境变量密钥管理 |

## 6. 阶段验收命令

```bash
python -m unittest discover -s tests
python -m compileall src tests examples
python -m src.engineer examples/review_target --use-llm-tests --mock-llm-response examples/llm_response/review_target_response.md --output docs/runs/software_engineer.json
python -m src.llm_tests examples/sample_python_project --mock-response examples/llm_response/pytest_response.md --output docs/runs/llm_tests.json
```

如需展示完整权限隔离闭环：

```bash
docker build -f Dockerfile.sandbox -t testguard-python .
python -m src.main examples/sample_python_project --generate-tests --executor docker --report-json docs/runs/sample_run.json
```
