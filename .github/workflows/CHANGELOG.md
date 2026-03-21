# 工作流变更日志

## [2.0.0] - 2026-03-21

### 重大变更

#### 触发方式
- **变更前**：自动触发（`release.published` 事件）
- **变更后**：手动触发（`workflow_dispatch`）
- **影响**：需要手动在 GitHub Actions 页面触发工作流

#### 执行方式
- **变更前**：在 GitHub Actions runner 上直接运行 Python 脚本
- **变更后**：向 API 服务器提交同步请求，异步处理
- **影响**：工作流快速返回，不等待上传完成

#### 安全性
- **变更前**：Token 明文传递
- **变更后**：RSA 4096 位加密传输
- **影响**：显著提升安全性

### 新增功能

#### 手输入参数
- `github_release_url`：GitHub Release 的完整 URL（必填）
- `gitcode_repo_url`：GitCode 仓库的完整 URL（必填）

#### 新增配置项
- `API_SERVER_URL`：API 服务器地址（Repository Variable）
- `API_KEY`：API 服务器认证密钥（Repository Secret）

#### 新增步骤
1. **Validate configuration**：验证必需的配置项
2. **Get public key from API server**：从 API 服务器获取 RSA 公钥
3. **Encrypt GitCode token**：使用 RSA 公钥加密 GitCode Token
4. **Submit sync request to API server**：向 API 服务器提交同步请求
5. **Summary**：生成执行摘要

### 移除功能

#### 移除的步骤
- **Checkout**：不再需要检出代码
- **Validate release assets directory**：不再需要本地文件验证
- **Upload artifacts to GitCode**：由 API 服务器处理

#### 移除的环境变量
- `GITCODE_REPO_URL`：改为通过输入参数提供
- `GITCODE_RELEASE_NAME`：由 API 服务器自动解析
- `GITCODE_RELEASE_BODY`：由 API 服务器自动解析

### 改进

#### 安全性
- ✅ RSA 4096 位非对称加密
- ✅ Token 明文只在内存中存在
- ✅ 加密后通过 HTTPS 传输
- ✅ API 密钥存储在 GitHub Secrets 中
- ✅ 不在日志中输出敏感信息

#### 性能
- ✅ 工作流快速返回（秒级）
- ✅ 异步处理大文件上传
- ✅ 减少 GitHub Actions 资源消耗
- ✅ 零磁盘占用

#### 灵活性
- ✅ 可同步任意 GitHub Release
- ✅ 支持多仓库配置
- ✅ 不依赖 Release 事件

#### 可维护性
- ✅ 逻辑集中在 API 服务器
- ✅ 工作流文件简洁
- ✅ 完整的错误处理
- ✅ 详细的日志输出

### 迁移指南

#### 如果使用旧版本

1. **部署 API 服务器**
   ```bash
   docker build -t release2gitcode .
   docker run -d -p 8000:8000 -e REQUIRE_HTTPS=false release2gitcode
   ```

2. **配置 GitHub 仓库**
   - 添加 Secret `API_KEY`
   - 添加 Secret `GITCODE_TOKEN`
   - 添加 Variable `API_SERVER_URL`

3. **触发工作流**
   - 进入 Actions 页面
   - 选择 "Sync Release To GitCode"
   - 填写 GitHub Release URL 和 GitCode 仓库 URL
   - 点击 Run workflow

#### 回滚到旧版本

如果需要回滚，可以：

1. 恢复原有的 `release-to-gitcode.yml` 文件
2. 配置 `GITCODE_TOKEN` 和 `GITCODE_REPO_URL`
3. 确保 `release_assets/` 目录存在并包含待上传文件

### 兼容性

#### 不兼容的变更
- ❌ 不再支持自动触发
- ❌ 不再支持本地文件上传
- ❌ 不再支持 `GITCODE_REPO_URL` 环境变量

#### 兼容的配置
- ✅ `GITCODE_TOKEN` Secret 仍然需要
- ✅ GitCode 仓库 URL 仍然需要（通过输入参数提供）

### 文档

#### 新增文档
- [README.md](./README.md) - 完整配置说明
- [QUICKSTART.md](./QUICKSTART.md) - 快速开始指南
- [CHANGELOG.md](./CHANGELOG.md) - 变更日志（本文件）

#### 更新文档
- [../../README.md](../../README.md) - 项目主 README
- [../../.trae/documents/rewrite-workflow-plan.md](../../.trae/documents/rewrite-workflow-plan.md) - 实施计划

### 测试

#### 测试清单
- [x] YAML 语法验证
- [x] 配置验证逻辑
- [x] 公钥获取逻辑
- [x] Token 加密逻辑
- [x] API 请求构造
- [x] 错误处理
- [ ] 集成测试（需要 API 服务器）
- [ ] 安全测试（需要 API 服务器）

### 已知问题

无

### 修复记录

#### 2026-03-21
- ✅ 修复：在配置验证步骤中添加 `jq` 命令安装检查
- ✅ 修复：错误提示信息中的语法错误（"set up following" → "set up following"）
- ✅ 增强：添加对 `github_release_url` 和 `gitcode_repo_url` 输入参数的格式验证
  - 验证 GitHub Release URL 格式：`https://github.com/owner/repo/releases/tag/v1.0.0`
  - 验证 GitCode 仓库 URL 格式：`https://gitcode.com/owner/repo`
  - 检查 URL 是否为空

### 未来计划

- [ ] 添加工作流自动触发选项（可选）
- [ ] 添加任务状态查询功能
- [ ] 添加任务取消功能
- [ ] 添加进度报告功能

---

## [1.0.0] - 初始版本

### 功能
- 自动触发（`release.published` 事件）
- 直接在 GitHub Actions runner 上运行 Python 脚本
- 上传本地 `release_assets/` 目录中的文件
- Token 明文传递

### 配置
- `GITCODE_TOKEN`：GitCode 访问令牌
- `GITCODE_REPO_URL`：GitCode 仓库地址
- `GITCODE_RELEASE_NAME`：Release 名称（可选）
- `GITCODE_RELEASE_BODY`：Release 描述（可选）
