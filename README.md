# Release2GitCode

`Release2GitCode` 用于把 GitHub Release 同步到 GitCode Release，现在提供两种正式入口：

- CLI 客户端：适合本地执行、CI 直接上传、本地排障。
- FastAPI 服务端：适合集中管理 API Key、用 GitHub Actions 通过加密请求触发同步。

当前仓库已经重构为共享核心库 + 双入口结构，避免此前 CLI 脚本和服务端分别维护两套上传逻辑。

## 架构

```text
src/release2gitcode/
  core/    共享能力：URL 解析、GitHub/GitCode API、流式同步、通知、配置
  cli/     CLI 入口
  server/  FastAPI 服务端入口
tests/     单元与接口测试
.github/workflows/
  release-to-gitcode.yml   GitHub Actions 示例
```

## 核心特性

- 共享同步核心：CLI 和服务端复用同一套 GitHub/GitCode 同步实现。
- 严格流式传输：大文件下载后直接上传，不落盘。
- ServerChan3 可选通知：`SendKey` 可存于 GitHub Secrets，经 RSA 公钥加密后和 GitCode Token 一样传输。
- API 认证：服务端使用 API Key + RSA 公钥加密，GitCode Token 和 `ServerChan3 SendKey` 不以明文出现在请求体中。
- Docker 就绪：服务端镜像仅包含运行所需文件。

## 安装

本地安装运行版：

```bash
pip install .
```

安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

## CLI 用法

查看帮助：

```bash
release2gitcode --help
```

### 1. 直接同步 GitHub Release 到 GitCode

```bash
release2gitcode sync-github \
  --github-release-url https://github.com/owner/repo/releases/tag/v1.0.0 \
  --gitcode-repo-url https://gitcode.com/owner/repo \
  --gitcode-token YOUR_GITCODE_TOKEN
```

如果需要同步完成后推送 ServerChan3：

```bash
release2gitcode sync-github \
  --github-release-url https://github.com/owner/repo/releases/tag/v1.0.0 \
  --gitcode-repo-url https://gitcode.com/owner/repo \
  --gitcode-token YOUR_GITCODE_TOKEN \
  --serverchan3-sendkey YOUR_SERVERCHAN3_SENDKEY
```

如果需要提升 GitHub API 配额或访问私有仓库，可以追加 GitHub token：

```bash
release2gitcode sync-github \
  --github-release-url https://github.com/owner/repo/releases/tag/v1.0.0 \
  --gitcode-repo-url https://gitcode.com/owner/repo \
  --gitcode-token YOUR_GITCODE_TOKEN \
  --github-token YOUR_GH_TOKEN
```

### 2. 上传本地构建产物到 GitCode Release

支持命令参数：

```bash
release2gitcode upload-local \
  --repo-url https://gitcode.com/owner/repo \
  --tag v1.0.0 \
  --token YOUR_GITCODE_TOKEN \
  --file release_assets/artifact-a.zip \
  --file release_assets/artifact-b.tar.gz
```

也支持环境变量模式。默认会读取 `release_assets/` 目录中的文件：

```bash
export GITCODE_TOKEN=YOUR_GITCODE_TOKEN
export GITCODE_REPO_URL=https://gitcode.com/owner/repo
export GITCODE_TAG=v1.0.0
release2gitcode upload-local
```

### 3. 用 CLI 加密机密

该命令主要供 GitHub Actions 或手工调试服务端 API 使用：

```bash
release2gitcode encrypt --public-key-file public.pem --secret YOUR_SECRET
```

也可以从环境变量读取：

```bash
export PUBLIC_KEY="$(cat public.pem)"
export GITCODE_TOKEN=YOUR_GITCODE_TOKEN
release2gitcode encrypt --public-key-env PUBLIC_KEY --secret-env GITCODE_TOKEN
```

## 服务端部署

服务端暴露两个主要接口：

- `GET /api/v1/public-key`
- `POST /api/v1/sync`

### 启动方式

直接运行：

```bash
python -m release2gitcode.server.main
```

或使用 Docker：

```bash
docker build -t release2gitcode .
docker run -p 8000:8000 -e REQUIRE_HTTPS=false -e API_KEY=YOUR_64_CHAR_API_KEY release2gitcode
```

或使用 Docker Compose：

```bash
cp .env.example .env
docker compose up -d --build
```

Compose 文件见：

- [docker-compose.yml](/c:/GitHub/Release2GitCode/docker-compose.yml)
- [.env.example](/c:/GitHub/Release2GitCode/.env.example)

### Docker Compose 部署流程

先复制环境变量模板：

```bash
cp .env.example .env
```

然后编辑 `.env`，至少确认：

- `PUBLISHED_PORT`
- `REQUIRE_HTTPS`
- `API_KEY` 或 `API_KEY_HASH`
- `DATA_DIR`

#### 方式 A：推荐，手动准备固定 64 位 API Key

先自己生成一个 64 位 API Key，例如：

```bash
python - <<'PY'
import secrets
import string
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*()"
print("".join(secrets.choice(chars) for _ in range(64)))
PY
```

然后把它填进 `.env` 里的 `API_KEY=`，再启动：

```bash
docker compose up -d --build
```

查看健康状态：

```bash
curl http://127.0.0.1:8000/health
```

获取公钥测试：

```bash
curl -H "X-API-Key: YOUR_64_CHAR_API_KEY" http://127.0.0.1:8000/api/v1/public-key
```

#### 方式 B：让容器首次启动自动生成 API Key

如果你在 `.env` 中留空 `API_KEY` 和 `API_KEY_HASH`，容器首次启动时会：

1. 自动生成一个随机 64 位 API Key
2. 把它打印到容器日志
3. 自动计算 `API_KEY_HASH`
4. 把哈希持久化到 `./data/api_key_hash`

启动命令：

```bash
docker compose up -d --build
```

首次启动后立刻查看日志并保存 API Key：

```bash
docker logs release2gitcode
```

你会看到类似输出：

```text
Generated a new 64-character API key for this container.
Store it securely before restarting:
<这里是生成出的64位API_KEY>
```

建议：

- 自动生成方式只适合首次快速部署或测试环境
- 生产环境更推荐你手动生成并固定 `API_KEY`
- 一旦丢失首次生成的明文 API Key，就只能改用新的 `API_KEY` 或 `API_KEY_HASH` 重新部署
- `.env` 不应提交到仓库；仓库只提供 `.env.example`

### 服务端环境变量

| 变量 | 必填 | 默认值 | 作用范围 | 说明 |
|---|---|---:|---|---|
| `HOST` | 否 | `0.0.0.0` | Server | 服务监听地址 |
| `PORT` | 否 | `8000` | Server | 服务监听端口 |
| `REQUIRE_HTTPS` | 否 | `true` | Server | 是否强制要求 HTTPS 或 `X-Forwarded-Proto=https` |
| `API_KEY` | 条件必填 | - | Server | 明文 API Key，仅用于首次启动计算哈希 |
| `API_KEY_HASH` | 条件必填 | - | Server | 已计算好的 bcrypt 哈希；优先级高于持久化文件 |
| `GITHUB_API_BASE` | 否 | `https://api.github.com` | Core | GitHub API 基地址 |
| `GITCODE_API_BASE` | 否 | `https://api.gitcode.com/api/v5` | Core | GitCode API 基地址 |
| `CHUNK_SIZE` | 否 | `1048576` | Core | 流式分块大小 |
| `UPLOAD_ATTEMPTS` | 否 | `5` | Core | 上传重试次数 |
| `HTTP_TIMEOUT_SECONDS` | 否 | `30.0` | Core | 默认 HTTP 超时 |
| `HTTP_MAX_CONNECTIONS` | 否 | `100` | Core | 连接池最大连接数 |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | 否 | `20` | Core | Keep-alive 连接数 |
| `RETRY_DELAY_SECONDS` | 否 | `1.0` | Core | 重试等待秒数 |

说明：

- `ServerChan3 SendKey` 不在服务端长期保存。
- `ServerChan3 SendKey` 如果需要，只通过每次 `/api/v1/sync` 请求中的加密字段传入。
- 服务端仅持久化 `API_KEY_HASH` 到 `/data/api_key_hash`。

## `/api/v1/sync` 请求体

```json
{
  "github_release_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
  "gitcode_repo_url": "https://gitcode.com/owner/repo",
  "encrypted_GH_TOKEN": "base64-rsa-ciphertext",
  "encrypted_gitcode_token": "base64-rsa-ciphertext",
  "encrypted_serverchan3_sendkey": "base64-rsa-ciphertext"
}
```

其中：

- `encrypted_gitcode_token` 必填。
- `encrypted_GH_TOKEN` 可选，提供后服务端会用它访问 GitHub Release API。
- `encrypted_serverchan3_sendkey` 可选。
- 如果未提供 `encrypted_serverchan3_sendkey`，同步照常进行，只是不会推送通知。

## GitHub Actions 集成

工作流示例文件：

- [release-to-gitcode.yml](/c:/GitHub/Release2GitCode/.github/workflows/release-to-gitcode.yml)

推荐配置：

| 类型 | 名称 | 必填 | 说明 |
|---|---|---|---|
| Secret | `API_KEY` | 是 | 服务端 API 认证密钥 |
| Secret | `GH_TOKEN` | 否 | GitHub API 令牌，用于更高速率限制或访问私有仓库 |
| Secret | `GITCODE_TOKEN` | 是 | GitCode 访问令牌 |
| Secret | `SERVERCHAN3_SENDKEY` | 否 | ServerChan3 推送密钥 |
| Variable | `API_SERVER_URL` | 是 | 部署后的 API 服务地址 |

工作流流程：

1. 获取服务端公钥。
2. 如果存在 `GH_TOKEN`，先加密并附带提交。
3. 使用 `release2gitcode encrypt` 加密 `GITCODE_TOKEN`。
4. 如果存在 `SERVERCHAN3_SENDKEY`，同样加密。
5. 提交 `/api/v1/sync` 请求。

## Docker

镜像仅包含：

- `pyproject.toml`
- `src/`
- `docker-entrypoint.sh`

入口脚本行为：

1. 从 `/data/api_key_hash` 加载或生成 `API_KEY_HASH`
2. 若只提供 `API_KEY`，自动计算 bcrypt 哈希并持久化
3. 启动 `python -m release2gitcode.server.main`

如果使用 Docker Compose，以上变量通常通过 `.env` 提供，无需手改 `docker-compose.yml`。

### API Key 说明

`API_KEY` 必须是 64 个字符。

你有两种选择：

- 手动制作并通过 `API_KEY` 传入
- 不传 `API_KEY`，让容器首次启动时自动生成

推荐结论：

- 测试环境：可以自动生成
- 生产环境：建议手动制作并保存，避免首次日志里的明文密钥丢失

## ServerChan3 说明

参考官方文档：

- https://doc.sc3.ft07.com/zh/serverchan3
- https://doc.sc3.ft07.com/zh/serverchan3/server/api

当前实现规则：

- GitHub Actions 从 Secret `SERVERCHAN3_SENDKEY` 读取可选密钥。
- `GH_TOKEN`、`GITCODE_TOKEN`、`SERVERCHAN3_SENDKEY` 都先向服务端获取公钥，再加密后传输。
- 服务端在同步结束后调用 `https://<uid>.push.ft07.com/send/<sendkey>.send`。
- 推送失败不会影响主同步结果，只会附加告警信息。

## 测试

运行测试：

```bash
pytest
```

## 故障排查

- `401 missing_api_key` 或 `401 invalid_api_key`
  - 检查 `X-API-Key` 是否正确，长度是否为 64。
- `400 token_decryption_error`
  - 说明机密不是用当前服务端返回的公钥加密的，或密文损坏。
- `503 network_error`
  - 检查 GitHub API、GitCode API、ServerChan3 网络连通性。
  - 如果 GitHub 返回 rate limit exceeded，优先配置 `GH_TOKEN`。
- GitHub Actions 成功但没有推送通知
  - 检查是否配置了 `SERVERCHAN3_SENDKEY`。
  - 检查 SendKey 是否对应正确 `uid`。

## 相关文档

- [ChangeLog.md](/c:/GitHub/Release2GitCode/ChangeLog.md)
- [WARNINGS_FIXED.md](/c:/GitHub/Release2GitCode/WARNINGS_FIXED.md)
- [Workflow README](/c:/GitHub/Release2GitCode/.github/workflows/README.md)
- [Workflow Quickstart](/c:/GitHub/Release2GitCode/.github/workflows/QUICKSTART.md)
