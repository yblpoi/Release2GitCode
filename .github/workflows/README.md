# GitHub Actions Workflow Guide

本目录包含 `Release2GitCode` 的 GitHub Actions 使用说明。

## 工作流文件

- [release-to-gitcode.yml](/c:/GitHub/Release2GitCode/.github/workflows/release-to-gitcode.yml)

## 工作流职责

该工作流只做四件事：

1. 校验输入和必需配置。
2. 从服务端获取 RSA 公钥。
3. 用 CLI 加密可选的 `GH_TOKEN`、必需的 `GITCODE_TOKEN`，以及可选的 `SERVERCHAN3_SENDKEY`。
4. 提交 `/api/v1/sync` 请求。

上传、Release 创建、附件去重、通知发送都由服务端共享核心处理。

## 必需配置

### Repository Secrets

| 名称 | 必填 | 说明 |
|---|---|---|
| `API_KEY` | 是 | 服务端 API Key |
| `GH_TOKEN` | 否 | GitHub API 令牌，用于更高速率限制或私有仓库 |
| `GITCODE_TOKEN` | 是 | GitCode 访问令牌 |
| `SERVERCHAN3_SENDKEY` | 否 | ServerChan3 SendKey |

### Repository Variables

| 名称 | 必填 | 说明 |
|---|---|---|
| `API_SERVER_URL` | 是 | 例如 `https://sync.example.com` |

## 输入参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `github_release_url` | 是 | GitHub Release 完整 URL |
| `gitcode_repo_url` | 是 | GitCode 仓库 URL |

## 安全说明

- `GH_TOKEN`、`GITCODE_TOKEN` 不直接发送给服务端。
- `SERVERCHAN3_SENDKEY` 如果存在，也不直接发送给服务端。
- 三者都先使用服务端返回的 RSA 公钥加密，再放入请求体。
- 服务端只在当前请求内存中解密，不持久化这些机密。
