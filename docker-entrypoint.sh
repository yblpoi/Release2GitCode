#!/bin/bash
###
 # @Author: yblpoi 66136793+yblpoi@users.noreply.github.com
 # @Date: 2026-03-21 02:58:26
 # @LastEditors: yblpoi 66136793+yblpoi@users.noreply.github.com
 # @LastEditTime: 2026-03-21 03:54:12
 # @FilePath: \Release2GitCode\docker-entrypoint.sh
 # @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
### 
set -e

# 持久化存储配置
DATA_DIR="/data"
API_KEY_HASH_FILE="${DATA_DIR}/api_key_hash"

# 确保数据目录存在并设置正确权限
mkdir -p "${DATA_DIR}"
chmod 700 "${DATA_DIR}"

# 从持久化文件加载 API_KEY_HASH（如果存在且未通过环境变量提供）
if [ -z "$API_KEY_HASH" ] && [ -f "$API_KEY_HASH_FILE" ]; then
    echo "Loading API key hash from persistent storage..."
    API_KEY_HASH=$(cat "$API_KEY_HASH_FILE")
fi

# 自动生成 32 位 API 密钥（如果没有提供 API_KEY 且 API_KEY_HASH 不存在）
if [ -z "$API_KEY" ] && [ -z "$API_KEY_HASH" ]; then
    echo "Generating random 32-character API key..."
    # 使用 Python secrets 模块生成安全随机密钥
    API_KEY=$(python3 -c '
import secrets
import string
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*()"
api_key = "".join(secrets.choice(chars) for _ in range(32))
print(api_key)
')
    echo "Generated new API key (full): $API_KEY"
fi

# 如果提供了明文 API_KEY，计算 bcrypt 哈希并持久化
if [ -n "$API_KEY" ] && [ -z "$API_KEY_HASH" ]; then
    echo "Computing bcrypt hash of API key..."
    API_KEY_HASH=$(echo "$API_KEY" | python3 -c '
import bcrypt
import sys
api_key = sys.stdin.read().strip().encode("utf-8")
hashed = bcrypt.hashpw(api_key, bcrypt.gensalt())
print(hashed.decode("utf-8"))
')
    echo "API key hash computed successfully."
    # 保存到持久化存储
    echo "$API_KEY_HASH" > "$API_KEY_HASH_FILE"
    chmod 600 "$API_KEY_HASH_FILE"
    echo "API key hash saved to persistent storage."
    # 清除明文 API_KEY 环境变量
    unset API_KEY
fi

# 检查 API_KEY_HASH 是否设置
if [ -z "$API_KEY_HASH" ]; then
    echo "ERROR: API_KEY_HASH is not set. Either provide API_KEY (to generate hash) or set API_KEY_HASH directly."
    exit 1
fi

# 如果已经计算出哈希但文件不存在，保存它
if [ ! -f "$API_KEY_HASH_FILE" ]; then
    echo "$API_KEY_HASH" > "$API_KEY_HASH_FILE"
    chmod 600 "$API_KEY_HASH_FILE"
fi

export API_KEY_HASH

echo "Starting Release2GitCode API server..."
echo "Host: ${HOST:-0.0.0.0}"
echo "Port: ${PORT:-8000}"
echo "Require HTTPS: ${REQUIRE_HTTPS:-true}"

exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
