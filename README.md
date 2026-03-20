# Release2GitCode

通过 GitHub Actions 和 GitCode OpenAPI，将 GitHub Release 构建产物同步到 GitCode Release。

## 提供内容

- `scripts/upload_to_gitcode.py`
  - 零第三方依赖的 Python 上传脚本
  - 按 tag 幂等创建或更新 GitCode Release
  - 逐个上传构建产物到 GitCode Release
- `.github/workflows/release-to-gitcode.yml`
  - GitHub `release.published` 事件示例工作流
  - 演示如何收集产物并调用上传脚本

## 环境变量

```text
GITCODE_TOKEN             GitCode PAT，必填
GITCODE_REPO_URL          GitCode 仓库链接，必填，例如 https://gitcode.com/yblpoi/SuperPicky
GITCODE_RELEASE_NAME      可选，默认回退到 tag
GITCODE_RELEASE_BODY      可选，默认读取根目录 ChangeLog.md
GITCODE_FILES             可选，未提供时默认扫描 release_assets/
GITCODE_TARGET_BRANCH     可选，未提供时默认读取远端 default_branch
GITCODE_UPLOAD_ATTEMPTS   可选，默认 5
GITCODE_TIMEOUT           可选，默认不设超时
```

兼容说明：

- 老的 `GITCODE_OWNER` + `GITCODE_REPO` 仍然可用，但推荐改成只传 `GITCODE_REPO_URL`
- `GITCODE_TAG` 现在可选；未提供时会优先读取 GitHub Actions 的 tag 上下文，再回退到 `ChangeLog.md` 第一行标题，例如 `# Project / v1.2.3`

## 本地运行

默认方式：将待上传文件放到 `release_assets/` 目录，然后直接运行脚本。

```powershell
$env:GITCODE_TOKEN = "your-token"
$env:GITCODE_REPO_URL = "https://gitcode.com/your-owner/your-repo"

python scripts/upload_to_gitcode.py
```

如果你希望覆盖默认目录，也可以显式传入 `GITCODE_FILES`：

```powershell
$env:GITCODE_FILES = @"
release_assets\artifact-a.zip
release_assets\artifact-b.tar.gz
"@

python scripts/upload_to_gitcode.py
```

## 默认行为

- Release 说明文本默认读取根目录 `ChangeLog.md`
- Release tag 默认优先读取 GitHub Actions 的 tag 参数，再尝试从 `ChangeLog.md` 第一行标题中提取
- 目标分支默认读取 GitCode 仓库的 `default_branch`
- 上传前会先读取远端 release 的已有关联附件；同名文件会直接跳过，避免重复上传
- 上传默认最多尝试 5 次，且默认不设超时

## GitHub Actions 配置

在仓库中配置以下项：

- `secrets.GITCODE_TOKEN`
- `vars.GITCODE_REPO_URL`

工作流示例现在与本地脚本保持一致，默认直接读取仓库中的 `release_assets/` 目录。也就是说，你只需要在触发 release 前把待上传文件准备到 `release_assets/` 下即可；脚本和 CI 都会使用同一套默认行为。

## API 服务器模式

本项目现在提供一个带完整加密认证的 API 服务器，可以直接作为服务部署，接收 GitHub Release URL → GitCode Release 自动同步。

**特性：**
- **零磁盘占用：** 针对小硬盘容量服务器优化，流式逐个文件下载上传，不写入本地磁盘
- **完整安全机制：** RSA 4096 非对称加密 + bcrypt API 密钥认证
- **自动密钥生成：** 容器启动自动生成密钥，重启自动轮换

### 使用 Docker 运行

```bash
# 构建镜像
docker build -t release2gitcode .

# 运行（自动生成 API 密钥
docker run -p 8000:8000 -e REQUIRE_HTTPS=false release2gitcode
```

容器启动后会输出生成的 API 密钥（只显示前 8 字符），可以在日志中查看。

### 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `API_KEY` | 明文 API 密钥（64 位），提供后会自动计算哈希 | - |
| `API_KEY_HASH` | bcrypt 哈希后的 API 密钥，直接设置可跳过生成 | - |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8000` |
| `REQUIRE_HTTPS` | 是否强制要求 HTTPS | `true` |
| `RATE_LIMIT_PUBLIC_KEY` | 公钥接口限流 | `10/minute` |
| `RATE_LIMIT_SYNC` | 同步接口限流 | `5/minute` |

### 持久化存储

API 密钥哈希支持持久化存储，容器重启后保持不变。RSA 密钥对仍然保持每次重启重新生成，符合安全设计。

**使用 Docker 命名卷：**

```bash
# 创建命名卷
docker volume create release2gitcode-data

# 运行容器并使用数据卷
docker run -d -p 8000:8000 -v release2gitcode-data:/data -e REQUIRE_HTTPS=false release2gitcode:latest
```

**使用绑定挂载：**

```bash
mkdir -p ./data
chmod 700 ./data

docker run -d -p 8000:8000 -v $(pwd)/data:/data -e REQUIRE_HTTPS=false release2gitcode:latest
```

**权限说明：**
- 数据目录 `/data` 权限：`700`（仅 root 可读可写）
- API 哈希文件 `/data/api_key_hash` 权限：`600`（仅 root 可读可写）
- 保证数据安全性，防止未授权访问

**备份与恢复：**

```bash
# 备份
docker run --rm --volumes-from release2gitcode -v $(pwd):/backup \
  cp /data/api_key_hash /backup

# 恢复
docker run --rm --volumes-from release2gitcode -v $(pwd):/backup \
  cp /backup/api_key_hash /data/
```

**行为逻辑：**
1. 如果环境变量已设置 `API_KEY_HASH`，优先级最高，不加载持久化文件
2. 如果环境变量未设置 `API_KEY_HASH` 但持久化文件存在，从文件加载
3. 如果都不存在，自动生成新 API 密钥并保存到持久化文件
4. RSA 密钥对始终在内存生成，容器退出即销毁，每次重启重新生成

### API 使用流程

**1. 获取公钥

```bash
curl -H "X-API-Key: your-api-key" https://your-server/api/v1/public-key
```

响应示例：
```json
{
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
  "key_id": "uuid-string"
}
```

**2. 使用公钥加密 GitCode 令牌，然后调用同步接口

```bash
curl -X POST -H "X-API-Key: your-api-key" -H "Content-Type: application/json" \
-d '{
  "github_release_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
  "gitcode_repo_url": "https://gitcode.com/owner/repo",
  "encrypted_gitcode_token": "base64-encrypted-token"
}' \
https://your-server/api/v1/sync
```

### 客户端加密示例（Python）：

```python
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

# 加载服务器返回的公钥
public_key = serialization.load_pem_public_key(
    server_public_key_pem.encode('utf-8')
)

# 加密令牌
encrypted = public_key.encrypt(
    gitcode_token.encode('utf-8'),
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# base64 编码
encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
```

## GitHub Actions 配置

在仓库中配置以下项：

- `secrets.GITCODE_TOKEN`
- `vars.GITCODE_REPO_URL`

工作流示例现在与本地脚本保持一致，默认直接读取仓库中的 `release_assets/` 目录。也就是说，你只需要在触发 release 前把待上传文件准备到 `release_assets/` 下即可；脚本和 CI 都会使用同一套默认行为。

## 参考文档

- GitCode API 总览: <https://docs.gitcode.com/docs/apis/>
- 创建 Release: <https://docs.gitcode.com/docs/apis/post-api-v-5-repos-owner-repo-releases/>
- 获取上传地址: <https://docs.gitcode.com/docs/apis/get-api-v-5-repos-owner-repo-releases-tag-upload-url/>
