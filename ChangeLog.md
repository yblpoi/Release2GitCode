# Change Log

## 3.0.0 - 2026-03-21

本版本完成仓库级重构。

### 架构调整

- 将旧的 `app/` 与 `scripts/upload_to_gitcode.py` 两套实现合并为共享核心库。
- 新增 `src/release2gitcode/core`、`src/release2gitcode/cli`、`src/release2gitcode/server`。
- 将测试迁移到 `tests/`。

### 新增能力

- 新增标准 CLI 命令：
  - `release2gitcode upload-local`
  - `release2gitcode sync-github`
  - `release2gitcode encrypt`
- 服务端 `/api/v1/sync` 新增可选字段 `encrypted_serverchan3_sendkey`。
- 服务端 `/api/v1/sync` 新增可选字段 `encrypted_github_token`，用于带认证访问 GitHub Release API。
- GitHub Actions 工作流支持从 `SERVERCHAN3_SENDKEY` Secret 读取并加密传输可选通知密钥。
- GitHub Actions 工作流支持从 `GITHUB_TOKEN` Secret 读取并加密传输可选 GitHub API 令牌。
- 服务端支持同步完成后通过 ServerChan3 推送结果。

### 性能与实现

- CLI 与服务端复用同一套 GitHub/GitCode API 调用逻辑。
- 保持大文件流式同步，不落盘。
- 统一复用 `httpx` 连接池与超时配置。

### 交付层变更

- Dockerfile 改为构建安装 `release2gitcode` Python 包。
- `docker-entrypoint.sh` 改为直接启动 `python -m release2gitcode.server.main`。
- 文档全部重写为新结构和新命令。

## 2.0.0 - 2026-03-21

- 引入独立 API 服务模式。
- 提供公钥接口与加密同步接口。

## 1.0.0 - 初始版本

- 通过脚本将本地产物上传到 GitCode Release。
