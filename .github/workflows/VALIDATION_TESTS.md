# Workflow Validation Notes

当前工作流主要验证以下场景：

## 配置验证

- `API_SERVER_URL`、`API_KEY`、`GITCODE_TOKEN` 已配置
- 如配置 `GITHUB_TOKEN`，工作流也应能成功加密并提交
- `github_release_url` 符合 GitHub Release URL 格式
- `gitcode_repo_url` 符合 GitCode 仓库 URL 格式，允许 `.git` 后缀

## 加密验证

- 能成功从 `/api/v1/public-key` 获取公钥
- 若 `GITHUB_TOKEN` 存在，也能成功加密
- `release2gitcode encrypt` 能加密 `GITCODE_TOKEN`
- 若 `SERVERCHAN3_SENDKEY` 存在，也能成功加密

## 请求验证

- 仅在存在 `GITHUB_TOKEN` 时提交 `encrypted_github_token`
- 仅在存在 `SERVERCHAN3_SENDKEY` 时提交 `encrypted_serverchan3_sendkey`
- 未配置 `SERVERCHAN3_SENDKEY` 时工作流仍能成功完成

## 建议联调项

- 用测试仓库验证一次只传 `GITCODE_TOKEN`
- 再验证一次同时传 `GITCODE_TOKEN` 和 `SERVERCHAN3_SENDKEY`
- 检查服务端在通知失败时是否仍返回主同步结果
