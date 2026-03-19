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

## 参考文档

- GitCode API 总览: <https://docs.gitcode.com/docs/apis/>
- 创建 Release: <https://docs.gitcode.com/docs/apis/post-api-v-5-repos-owner-repo-releases/>
- 获取上传地址: <https://docs.gitcode.com/docs/apis/get-api-v-5-repos-owner-repo-releases-tag-upload-url/>
