# API Spec

## 1. 主入口

```bash
python -m src.engineer <project_path> [options]
```

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `project_path` | 是 | 待审查的 Python 项目路径。 |
| `--output` | 否 | JSON 报告路径，默认 `docs/runs/software_engineer.json`。 |
| `--output-md` | 否 | Markdown 报告路径，默认 `docs/runs/software_engineer.md`。 |
| `--apply-tests` | 否 | 将生成测试写回目标项目。默认 dry-run。 |
| `--apply-fixes` | 否 | 将 LLM 修复建议写回源码。默认 dry-run。 |
| `--run-sandbox` | 否 | 启用 sandbox validation。 |
| `--sandbox-executor` | 否 | `local` 或 `docker`，默认 `docker`。 |
| `--docker-image` | 否 | Docker 沙箱镜像。 |
| `--timeout` | 否 | 沙箱超时时间，默认 30 秒。 |
| `--repair-iterations` | 否 | repair loop 最大重试次数，默认 3。 |
| `--llm-test-file` | 否 | LLM 生成测试写回路径。 |
| `--max-functions` | 否 | 最多处理的公开函数数。 |

示例：

```bash
python -m src.engineer examples/review_target --run-sandbox --sandbox-executor docker --output docs/runs/software_engineer.json --output-md docs/runs/software_engineer.md
```

## 2. 辅助入口

```bash
python -m src.llm_tests <project_path> --output docs/runs/llm_tests.json
python -m src.benchmark --executor docker --output docs/runs/benchmark.json
```

## 3. JSON 报告结构

顶层字段：

- `project_path`
- `status`
- `graph_runtime`
- `node_trace`
- `summary`
- `scan`
- `llm_review`
- `llm_fix`
- `llm_tests`
- `sandbox_validation`
- `repair_loop`
- `coverage_feedback`

`summary` 字段：

- `generated_llm_test_count`
- `llm_fix_count`
- `apply_fixes`
- `apply_tests`
- `run_sandbox`
- `sandbox_executor`

## 4. LLM 配置

默认 provider 为 DashScope：

```bash
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_key
LLM_MODEL=glm-5.2
```

DeepSeek：

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key
LLM_MODEL=deepseek-v4-pro
```

报告只记录 `api_key_set` 和 `api_key_env`，不输出 API Key 明文。
