# Sandbox Security Policy

## 目标

第二阶段引入 Docker 沙箱执行器，用于降低自动生成测试代码对宿主机和用户源码的影响。该策略面向课程 Demo 和本地开发环境，重点展示权限隔离设计。

## 当前策略

Docker 执行器默认采用以下限制：

- `--network none`：禁用容器网络，降低数据外传和远程调用风险。
- `--mount type=bind,source=<project>,target=/workspace,readonly`：源码目录只读挂载，测试代码不能修改项目文件。
- `--read-only`：容器根文件系统只读。
- `--tmpfs /tmp:rw,size=128m`：仅开放有限临时写入空间。
- `--cpus 1`：限制 CPU 使用。
- `--memory 512m`：限制内存使用。
- `--pids-limit 128`：限制进程数量。
- `--cap-drop ALL`：移除 Linux capabilities。
- `--security-opt no-new-privileges`：禁止容器进程获取额外权限。
- 宿主进程 `timeout`：限制整体执行时间。

## 执行命令

```bash
docker build -f Dockerfile.sandbox -t software-engineer-agent-python .
python -m src.main examples/sample_python_project --executor docker
```

## 边界说明

该沙箱用于课程项目演示，不等同于生产级恶意代码执行平台。后续可进一步加入：

- 生成测试代码的 AST 安全检查。
- 独立临时工作目录和测试产物目录。
- seccomp / AppArmor 配置。
- Agent trace 与安全审计日志。

## 超时清理

每次 Docker 执行都会分配唯一容器名。如果宿主侧超时触发，Software Engineer Agent 会尝试执行
`docker rm -f <container_name>` 清理仍在运行的容器，避免异常测试任务在 CLI 退出后继续占用资源。
