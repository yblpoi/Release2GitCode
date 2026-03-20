# Release2GitCode API Server Dockerfile
# 使用官方 Python 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（编译 bcrypt 和 cryptography 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 添加执行权限给入口脚本
RUN chmod +x /app/docker-entrypoint.sh

# 暴露端口
EXPOSE 8000

# 入口脚本
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 声明数据卷用于持久化存储 API 密钥哈希
# 权限：700 for directory, 600 for file
VOLUME ["/data"]
