# Refactor Notes

本文件不再记录旧版 `app/` 目录中的历史告警修复明细，改为说明本次重构后如何避免同类问题。

## 已处理的问题类型

- 入口分散：旧版同时存在根目录脚本和服务端内部上传实现，逻辑重复。
- 目录职责混杂：客户端、服务端、上传逻辑、测试和文档没有稳定边界。
- 工作流内嵌业务逻辑：GitHub Actions 中直接写加密脚本，维护成本高。
- 运行镜像内容偏杂：Docker 构建入口依赖旧 `app/` 路径。

## 当前规避方式

- 使用 `src/release2gitcode/core` 作为唯一业务核心。
- CLI 和服务端仅保留薄入口，不再复制同步逻辑。
- GitHub Actions 改为调用 `release2gitcode encrypt`。
- Docker 改为直接安装包并调用模块入口。

## 后续关注点

- 如果未来新增新通知渠道，应放入 `src/release2gitcode/core/notifications.py` 或相邻模块，而不是把逻辑写回工作流。
- 如果未来新增新入口，优先复用 `ReleaseSyncService`，避免再次出现多套 GitCode 上传实现。
