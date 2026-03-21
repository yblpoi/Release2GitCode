# Workflow Change Log

## 2026-03-21

### 主要变化

- 工作流保留 API 服务模式，不再回退到仓库内旧脚本。
- 加密逻辑改为调用 CLI 命令 `release2gitcode encrypt`，不再在 YAML 中内嵌 Python 加密代码。
- 新增对可选 `SERVERCHAN3_SENDKEY` 的加密和传输支持。
- GitCode 仓库 URL 验证支持 `.git` 后缀。

### 结果

- 工作流职责更薄。
- 业务逻辑集中到共享核心与服务端。
- 机密处理路径统一。
