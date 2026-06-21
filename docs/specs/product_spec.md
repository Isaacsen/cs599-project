# Product Spec

## 1. 目标

Software Engineer Agent 面向 Python 项目，提供真实 LLM 语义审查、LLM 修复建议、LLM 测试生成、权限隔离执行、失败后回跳重试的修复循环和覆盖反馈。

当前版本不提供自动改写业务源码的 Bug Fix Agent，也不在主流程中使用规则 Review 或模板 Unit Test。系统输出 LLM 审查发现、LLM 测试结果和下一步建议，由用户或外部开发工具决定如何修改代码。

## 2. 用户场景

- 课程评审者需要看到一个可运行、可观测、可复现的 Agentic AI 项目。
- 开发者需要快速审查 Python 项目并补齐基础测试。
- 开发者需要把 LLM 生成代码放到隔离环境里验证。
- 开发者需要知道当前测试覆盖了哪些函数，还有哪些函数缺失覆盖。

## 3. 功能需求

| 编号 | 需求 |
| --- | --- |
| FR-1 | 扫描 Python 仓库并识别公开函数。 |
| FR-2 | 调用真实 LLM 执行语义代码审查。 |
| FR-3 | 调用真实 LLM 生成 pytest 测试。 |
| FR-6 | 对生成测试执行安全检查。 |
| FR-7 | 在 local 或 Docker 后端运行生成测试。 |
| FR-8 | 根据沙箱结果决定把失败诊断回送给 LLM Fix Agent 或 LLM Test Agent 重试。 |
| FR-9 | 输出覆盖反馈。 |
| FR-10 | 输出 JSON 和 Markdown 报告。 |
| FR-11 | LLM API Key 只能通过环境变量读取。 |

## 4. 非功能需求

- 默认不写回目标项目；写回测试必须显式传入 `--apply-tests`。
- Docker 沙箱应限制网络、文件系统写入和资源。
- 报告不得包含 API Key 明文。
- 主流程必须可在无 LLM 或无 Docker 的情况下以降级路径运行。

## 5. 主流程

```text
scan -> llm_review -> llm_fix -> llm_tests -> sandbox_validate? -> repair_loop? -> (llm_fix|llm_tests)* -> coverage_feedback -> finish
```
