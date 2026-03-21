"""API key validation helpers."""

from __future__ import annotations

from functools import lru_cache

import bcrypt

from release2gitcode.core.config import settings
from release2gitcode.core.errors import InvalidAPIKeyError, MissingAPIKeyError


@lru_cache(maxsize=1)
def _get_api_key_hash_bytes() -> bytes:
    return settings.api_key_hash.encode("utf-8")


def verify_api_key(api_key: str | None) -> bool:
    if not api_key or not settings.api_key_hash:
        return False
    if len(api_key) != settings.api_key_length:
        return False
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), _get_api_key_hash_bytes())
    except (TypeError, ValueError):
        return False


def extract_api_key(api_key_header: str | None) -> str:
    if not api_key_header:
        raise MissingAPIKeyError()
    api_key = api_key_header.strip()
    if not verify_api_key(api_key):
        raise InvalidAPIKeyError()
    return api_key


def get_api_key_hash_prefix(api_key_hash: str) -> str:
    return api_key_hash[:8] if len(api_key_hash) >= 8 else api_key_hash
