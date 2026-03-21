#!/bin/bash
###
 # @Author: yblpoi yblpoi@users.noreply.github.com
 # @Date: 2026-03-21 02:58:26
 # @LastEditors: yblpoi yblpoi@users.noreply.github.com
 # @LastEditTime: 2026-03-21 19:54:10
 # @FilePath: \Release2GitCode\docker-entrypoint.sh
 # @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
### 
set -e

DATA_DIR="/data"
API_KEY_HASH_FILE="${DATA_DIR}/api_key_hash"

mkdir -p "${DATA_DIR}"
chmod 700 "${DATA_DIR}"

if [ -z "$API_KEY_HASH" ] && [ -f "$API_KEY_HASH_FILE" ]; then
    API_KEY_HASH=$(cat "$API_KEY_HASH_FILE")
fi

if [ -z "$API_KEY" ] && [ -z "$API_KEY_HASH" ]; then
    API_KEY=$(python3 -c '
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
')
    echo "Generated a new 64-character API key for this container."
    echo "Store it securely before restarting:"
    echo "$API_KEY"
fi

if [ -n "$API_KEY" ] && [ -z "$API_KEY_HASH" ]; then
    API_KEY_HASH=$(echo "$API_KEY" | python3 -c '
import bcrypt
import sys
api_key = sys.stdin.read().strip().encode("utf-8")
hashed = bcrypt.hashpw(api_key, bcrypt.gensalt())
print(hashed.decode("utf-8"))
')
    echo "$API_KEY_HASH" > "$API_KEY_HASH_FILE"
    chmod 600 "$API_KEY_HASH_FILE"
    unset API_KEY
fi

if [ -z "$API_KEY_HASH" ]; then
    echo "ERROR: API_KEY_HASH is not set. Provide API_KEY or API_KEY_HASH."
    exit 1
fi

if [ ! -f "$API_KEY_HASH_FILE" ]; then
    echo "$API_KEY_HASH" > "$API_KEY_HASH_FILE"
    chmod 600 "$API_KEY_HASH_FILE"
fi

export API_KEY_HASH

echo "Starting Release2GitCode API server..."
echo "Timestamp (UTC): $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Host: ${HOST:-0.0.0.0}"
echo "Port: ${PORT:-8000}"
echo "Require HTTPS: ${REQUIRE_HTTPS:-true}"
echo "HTTP Timeout Seconds: ${HTTP_TIMEOUT_SECONDS:-30.0}"
echo "HTTP Max Connections: ${HTTP_MAX_CONNECTIONS:-100}"
echo "HTTP Max Keepalive Connections: ${HTTP_MAX_KEEPALIVE_CONNECTIONS:-20}"
echo "Upload Attempts: ${UPLOAD_ATTEMPTS:-5}"
echo "Chunk Size: ${CHUNK_SIZE:-1048576}"
echo "Sync Concurrency: ${SYNC_CONCURRENCY:-3}"
echo "Server Log Level: ${SERVER_LOG_LEVEL:-info}"
echo "Server Access Log: ${SERVER_ACCESS_LOG:-true}"

exec python -m release2gitcode.server.main
