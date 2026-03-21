# GitHub Actions 工作流配置说明

## 概述

`release-to.yml` 工作流已重写为手动触发模式，通过 API 服务器实现安全的 Release 同步。

## 主要变更

### 触发方式
- **旧版本**：自动触发（`release.published` 事件）
- **新版本**：手动触发（`workflow_dispatch`）

### 执行方式
- **旧版本**：在 GitHub Actions runner 上直接运行 Python 脚本
- **新版本**：向 API 服务器提交同步请求，异步处理

### 安全性
- **旧版本**：Token 明文传递
- **新版本**：RSA 4096 位加密传输

## 配置要求

### 1. GitHub 仓库配置

#### Secrets（密钥）
在 GitHub 仓库的 Settings → Secrets and variables → Actions 中配置：

| 名称 | 说明 | 示例 |
|------|------|------|
| `API_KEY` | API 服务器认证密钥 | `your-64-char-api-key` |
| `GITCODE_TOKEN` | GitCode 访问令牌 | `glpat-xxxxxxxxxxxx` |

#### Variables（变量）
在 GitHub 仓库的 Settings → Secrets and variables → Actions → Variables 中配置：

| 名称 | 说明 | 示例 |
|------|------|------|
| `API_SERVER_URL` | API 服务器地址 | `https://your-server.com` |

### 2. API 服务器配置

确保已部署 Release2GitCode API 服务器，并且：

1. 服务器可从 GitHub Actions 访问
2. 已配置 API 密钥
3. 服务器正常运行

## 使用方法

### 手动触发工作流

1. 进入 GitHub 仓库的 **Actions** 标签页
2. 选择 **Sync Release To GitCode** 工作流
3. 点击 **Run workflow** 按钮
4. 填写必填参数：
   - **GitHub Release URL**: GitHub Release 的完整 URL
     - 示例：`https://github.com/owner/repo/releases/tag/v1.0.0`
   - **GitCode repository URL**: GitCode 仓库的完整 URL
     - 示例：`https://gitcode.com/owner/repo`
5. 点击 **Run workflow** 提交

### 工作流执行流程

1. **验证配置**：检查必需的环境变量和密钥
2. **获取公钥**：从 API 服务器获取 RSA 公钥
3. **加密 Token**：使用公钥加密 GitCode Token
4. **提交请求**：向 API 服务器提交同步请求
5. **立即返回**：工作流快速返回，不等待上传完成

### 查看执行结果

工作流完成后，可以在 **Summary** 部分查看：

- **Task ID**：同步任务的唯一标识符
- **Status**：任务状态
- **Message**：任务消息

同步任务在 API 服务器上异步执行，可以使用 Task ID 追踪任务进度。

## 工作流步骤详解

### 1. Validate configuration
验证必需的配置项：
- `API_SERVER_URL`
- `API_KEY`
- `GITCODE_TOKEN`

### 2. Set up Python
设置 Python 3.x 环境

### 3. Install cryptography
安装 Python `cryptography` 库用于 RSA 加密

### 4. Get public key from API server
从 API 服务器获取 RSA 公钥：
- 调用 `GET /api/v1/public-key`
- 使用 `X-API-Key` 请求头认证
- 解析响应获取 `public_key` 和 `key_id`

### 5. Encrypt GitCode token
使用 RSA 公钥加密 GitCode Token：
- 使用 OAEP padding
- SHA-256 哈希算法
- Base64 编码输出

### 6. Submit sync request to API server
向 API 服务器提交同步请求：
- 调用 `POST /api/v1/sync`
- 请求体包含：
  - `github_release_url`
  - `gitcode_repo_url`
  - `encrypted_gitcode_token`
- 解析响应获取任务信息

### 7. Summary
生成执行摘要，显示任务 ID 和状态

## 安全特性

### 1. Token 加密
- 使用 RSA 4096 位公钥加密
- Token 明文只在内存中存在
- 加密后通过 HTTPS 传输

### 2. API 密钥保护
- 存储在 GitHub Secrets 中
- 通过请求头传递
- 不在日志中输出

### 3. 错误处理
- 不在错误消息中泄露敏感信息
- 每个步骤都有完整的错误检查

### 4. 审计日志
- 记录任务 ID
- 记录操作时间戳
- 不记录敏感数据

## 故障排查

### 配置错误
```
Error: Missing required configuration: API_SERVER_URL
```
**解决方案**：检查 GitHub 仓库的 Variables 和 Secrets 配置

### API 服务器连接失败
```
Error: Failed to get public key (HTTP 502)
```
**解决方案**：
1. 检查 API 服务器是否正常运行
`2. 检查 API_SERVER_URL 是否正确`
3. 检查网络连接

### API 密钥认证失败
```
Error: Failed to get public key (HTTP 401)
```
**解决方案**：
1. 检查 API_KEY 是否正确
2. 检查 API 服务器配置

### Token 加密失败
```
Error: Invalid response - public_key not found
```
**解决方案**：
1. 检查 API 服务器响应格式
2. 检查 API 服务器版本

### 同步请求提交失败
```
Error: Failed to submit sync request (HTTP 400)
```
**解决方案**：
1. 检查输入的 URL 格式是否正确
2. 检查 API 服务器日志获取详细错误信息

## 优势对比

| 特性 | 旧版本 | 新版本 |
|------|--------|--------|
| 触发方式 | 自动 | 手动 |
| 执行位置 | GitHub Actions | API 服务器 |
| Token 安全 | 明文传输 | RSA 加密 |
| 磁盘占用 | 需要本地文件 | 零磁盘占用 |
| 执行时间 | 等待上传完成 | 立即返回 |
| 灵活性 | 仅限当前仓库 | 可同步任意 Release |
| 资源消耗 | 高 | 低 |

## 回滚方案

如果需要回滚到旧版本：

1. 恢复原有的 `release-to-gitcode.yml` 文件
2. 配置 `GITCODE_TOKEN` 和 `GITCODE_REPO_URL`
3. 确保 `release_assets/` 目录存在并包含待上传文件

## 相关文档

- [Release2GitCode README](../../README.md)
- [API 服务器文档](../../README.md#api-服务器模式)
- [实施计划](../../.trae/documents/rewrite-workflow-plan.md)
