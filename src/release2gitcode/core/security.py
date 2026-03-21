"""API key validation helpers."""

from __future__ import annotations

from functools import lru_cache

import bcrypt
import string

from release2gitcode.core.config import settings
from release2gitcode.core.errors import InvalidAPIKeyError, InvalidAPIKeyFormatError, MissingAPIKeyError

API_KEY_PREFIX = "r2gc-"
API_KEY_LENGTH = 64
API_KEY_ALLOWED_CHARS = set(
    string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
)


@lru_cache(maxsize=1)
def _get_api_key_hash_bytes() -> bytes:
    return settings.api_key_hash.encode("utf-8")


def validate_api_key_format(api_key: str) -> bool:
    """验证API密钥格式是否符合规范"""
    if not api_key:
        return False
    if len(api_key) != API_KEY_LENGTH:
        return False
    if not api_key.startswith(API_KEY_PREFIX):
        return False
    return all(char in API_KEY_ALLOWED_CHARS for char in api_key)


def verify_api_key(api_key: str | None) -> bool:
    if not api_key or not settings.api_key_hash:
        return False
    if not validate_api_key_format(api_key):
        return False
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), _get_api_key_hash_bytes())
    except (TypeError, ValueError):
        return False


def extract_api_key(api_key_header: str | None) -> str:
    if not api_key_header:
        raise MissingAPIKeyError()
    api_key = api_key_header.strip()
    if not validate_api_key_format(api_key):
        raise InvalidAPIKeyFormatError()
    if not verify_api_key(api_key):
        raise InvalidAPIKeyError()
    return api_key


def get_api_key_hash_prefix(api_key_hash: str) -> str:
    return api_key_hash[:8] if len(api_key_hash) >= 8 else api_key_hash
