# 快速开始指南

## 前置条件

1. 已部署 Release2GitCode API 服务器
2. 已获取 API 服务器地址和 API 密钥
3. 已获取 GitCode 访问令牌

## 配置步骤

### 1. 配置 GitHub 仓库 Secrets

在 GitHub 仓库中导航到：
`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加以下 Secrets：

| 名称 | 值 |
|------|-----|
| `API_KEY` | API 服务器的 64 字符认证密钥 |
| `GITCODE_TOKEN` | GitCode 访问令牌（glpat-xxxxx） |

### 2. 配置 GitHub 仓库 Variables

在 GitHub 仓库中导航到：
`Settings` → `Secrets and variables` → `Actions` → `Variables` → `New repository variable`

添加以下 Variable：

| 名称 | 值 |
|------|-----|
| `API_SERVER_URL` | API 服务器地址（如 https://your-server.com） |

## 使用步骤

### 触发工作流

1. 进入 GitHub 仓库的 **Actions** 标签页
2. 在左侧选择 **Sync Release To GitCode** 工作流
3. 点击右侧的 **Run workflow** 按钮
4. 填写表单：
   ```
   GitHub Release URL: https://github.com/owner/repo/releases/tag/v1.0.0
   GitCode repository URL: https://gitcode.com/owner/repo
   ```
5. 点击绿色的 **Run workflow** 按钮

### 查看结果

工作流执行完成后：

1. 点击工作流运行记录
2. 滚动到页面底部的 **Summary** 部分
3. 查看 **Task ID**，可用于追踪同步任务

## 示例

### 同步 GitHub Release 到 GitCode

**输入：**
- GitHub Release URL: `https://github.com/vuejs/core/releases/tag/v3.4.0`
- GitCode repository URL: `https://gitcode.com/myorg/vue-core`

**输出：**
```
Sync request submitted successfully!
Task ID: 550e8400-e29b-41d4-a716-446655555555
Status: completed
Message: Synchronization completed. Processed 5 assets, skipped 0, failed 0.
```

## 常见问题

### Q: 工作流提示 "Missing required configuration"
**A:** 检查 GitHub 仓库的 Secrets 和 Variables 是否正确配置

### Q: 工作流提示 "Failed to get public key"
**A:** 检查 API_SERVER_URL 是否正确，API 服务器是否正常运行

### Q: 工作流提示 "Failed to submit sync request"
**A:** 检查输入的 URL 格式是否正确，查看 API 服务器日志

### Q: 如何追踪同步任务进度？
**A:** 使用工作流 Summary 中显示的 Task ID 在 API 服务器日志中查询

## 相关链接

- [完整配置说明](./README.md)
- [实施计划](../../.trae/documents/rewrite-workflow-plan.md)
- [项目 README](../../README.md)
