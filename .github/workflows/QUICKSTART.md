# Workflow Quickstart

## 1. 部署服务端

```bash
docker build -t release2gitcode .
docker run -d -p 8000:8000 -e REQUIRE_HTTPS=false -e API_KEY=YOUR_64_CHAR_API_KEY release2gitcode
```

## 2. 配置 GitHub 仓库

### Secrets

- `API_KEY`
- `GITHUB_TOKEN`（可选）
- `GITCODE_TOKEN`
- `SERVERCHAN3_SENDKEY`（可选）

### Variables

- `API_SERVER_URL`

## 3. 触发工作流

在 GitHub Actions 页面运行 `Sync Release To GitCode`，并填写：

- `github_release_url`
- `gitcode_repo_url`

## 4. 查看结果

工作流结束后在 Summary 中查看：

- `task_id`
- `status`
- `message`

如果配置了 `SERVERCHAN3_SENDKEY`，同步完成后还会收到推送。
