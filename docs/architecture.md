# TestGuard Agent Architecture

## 当前阶段架构

```mermaid
flowchart TD
    A["用户输入 Python 项目路径"] --> B["Repo Scanner"]
    B --> C{"是否生成测试"}
    C --> D["Test Generator Agent"]
    D --> E["临时测试工作区"]
    C --> F{"选择执行后端"}
    E --> F
    F --> G["Local Pytest Executor"]
    F --> H["Docker Sandbox Executor"]
    H --> I["权限隔离策略"]
    I --> J["网络禁用 / 只读挂载 / 资源限制"]
    G --> K["Pipeline Report"]
    J --> K
    K --> L["CLI 输出"]
```

## 目标阶段架构

```mermaid
flowchart TD
    A["用户提交代码仓库"] --> B["Repo Analyzer Agent"]
    B --> C["Test Planner Agent"]
    C --> D["Test Generator Agent"]
    D --> E["Security Checker"]
    E --> F["Sandbox Executor"]
    F --> G["Result Analyzer Agent"]
    G --> H["测试报告 / 失败诊断 / 修复建议"]

    B --> I["代码索引"]
    F --> J["Docker 权限隔离层"]
    J --> K["只读源码挂载"]
    J --> L["网络禁用"]
    J --> M["CPU / 内存 / 时间限制"]
```

## 第一阶段验收标准

运行以下命令：

```bash
python -m src.main examples/sample_python_project
```

系统能够完成项目扫描、pytest 执行和命令行报告输出。

## 第二阶段验收标准

运行以下命令：

```bash
docker build -f Dockerfile.sandbox -t testguard-python .
python -m src.main examples/sample_python_project --executor docker
```

系统能够在 Docker 沙箱中完成项目扫描、pytest 执行和命令行报告输出。

## 第三阶段验收标准

运行以下命令：

```bash
python -m src.main examples/sample_python_project --generate-tests --executor docker
```

系统能够自动生成 pytest 测试，在临时工作区中执行，并在报告中展示生成测试数量。
