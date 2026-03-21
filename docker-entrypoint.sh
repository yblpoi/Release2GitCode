#!/bin/bash
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
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*()"
api_key = "".join(secrets.choice(chars) for _ in range(64))
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
echo "Host: ${HOST:-0.0.0.0}"
echo "Port: ${PORT:-8000}"
echo "Require HTTPS: ${REQUIRE_HTTPS:-true}"

exec python -m release2gitcode.server.main
