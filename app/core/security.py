"""API 密钥安全验证"""

import bcrypt
from functools import lru_cache

from app.config.settings import settings
from app.exceptions.errors import MissingAPIKeyError, InvalidAPIKeyError


@lru_cache(maxsize=1)
def _get_api_key_hash_bytes() -> bytes:
    """缓存 API_KEY_HASH 的 bytes 形式，避免每次请求重复编码。"""

    return settings.api_key_hash.encode("utf-8")


def verify_api_key(api_key: str | None) -> bool:
    """验证 API 密钥

    Args:
        api_key: 客户端提供的 API 密钥

    Returns:
        True 验证通过，False 验证失败
    """

    if not api_key:
        return False

    if not settings.api_key_hash:
        return False

    if len(api_key) != settings.api_key_length:
        return False

    try:
        return bcrypt.checkpw(
            api_key.encode("utf-8"),
            _get_api_key_hash_bytes(),
        )
    except (ValueError, TypeError):
        return False


def extract_api_key(api_key_header: str | None) -> str:
    """从请求头提取 API 密钥并验证

    Args:
        api_key_header: X-API-Key 请求头值

    Returns:
        验证通过返回 API 密钥

    Raises:
        MissingAPIKeyError: 缺少 API 密钥
        InvalidAPIKeyError: API 密钥无效
    """

    if not api_key_header:
        raise MissingAPIKeyError()

    api_key = api_key_header.strip()
    if not verify_api_key(api_key):
        raise InvalidAPIKeyError()

    return api_key


def get_api_key_hash_prefix(api_key_hash: str) -> str:
    """获取 API 密钥哈希的前缀，用于日志标识，不暴露完整哈希

    Args:
        api_key_hash: 完整哈希

    Returns:
        前缀（前 8 字符）
    """

    return api_key_hash[:8] if len(api_key_hash) >= 8 else api_key_hash
