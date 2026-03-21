"""测试API密钥安全验证功能"""

import pytest
import bcrypt

from release2gitcode.core.security import (
    validate_api_key_format,
    verify_api_key,
    API_KEY_PREFIX,
    API_KEY_LENGTH,
    API_KEY_ALLOWED_CHARS,
)
from release2gitcode.core.errors import InvalidAPIKeyFormatError, InvalidAPIKeyError, MissingAPIKeyError


def test_validate_api_key_format_valid():
    """测试有效的API密钥格式"""
    valid_key = "r2gc-" + "A" * 59
    assert validate_api_key_format(valid_key) is True


def test_validate_api_key_format_with_mixed_chars():
    """测试包含混合字符的有效API密钥"""
    valid_key = "r2gc-AbC123-xYz789-aBc123-" + "A" * 38
    assert len(valid_key) == 64
    assert validate_api_key_format(valid_key) is True


def test_validate_api_key_format_empty():
    """测试空密钥"""
    assert validate_api_key_format("") is False


def test_validate_api_key_format_none():
    """测试None密钥"""
    assert validate_api_key_format(None) is False


def test_validate_api_key_format_wrong_length():
    """测试长度不正确的密钥"""
    too_short = "r2gc-" + "A" * 58
    too_long = "r2gc-" + "A" * 60
    assert validate_api_key_format(too_short) is False
    assert validate_api_key_format(too_long) is False


def test_validate_api_key_format_wrong_prefix():
    """测试前缀不正确的密钥"""
    wrong_prefix = "abc-" + "A" * 59
    no_prefix = "A" * 64
    assert validate_api_key_format(wrong_prefix) is False
    assert validate_api_key_format(no_prefix) is False


def test_validate_api_key_format_invalid_chars():
    """测试包含非法字符的密钥"""
    with_special_chars = "r2gc-" + "A" * 58 + "!"
    with_space = "r2gc-" + "A" * 58 + " "
    with_underscore = "r2gc-" + "A" * 58 + "_"
    assert validate_api_key_format(with_special_chars) is False
    assert validate_api_key_format(with_space) is False
    assert validate_api_key_format(with_underscore) is False


def test_api_key_constants():
    """测试API密钥常量定义"""
    assert API_KEY_PREFIX == "r2gc-"
    assert API_KEY_LENGTH == 64
    assert len(API_KEY_ALLOWED_CHARS) == 26 + 26 + 10 + 1  # 大写字母 + 小写字母 + 数字 + 连字符


def test_extract_api_key_missing():
    """测试缺少API密钥"""
    from release2gitcode.core.security import extract_api_key
    
    with pytest.raises(MissingAPIKeyError):
        extract_api_key(None)
    
    with pytest.raises(MissingAPIKeyError):
        extract_api_key("")


def test_extract_api_key_invalid_format():
    """测试格式无效的API密钥"""
    from release2gitcode.core.security import extract_api_key
    
    invalid_key = "invalid-key-format"
    with pytest.raises(InvalidAPIKeyFormatError):
        extract_api_key(invalid_key)


def test_extract_api_key_invalid_hash():
    """测试哈希无效的API密钥"""
    from release2gitcode.core.security import extract_api_key
    from release2gitcode.core.config import settings
    
    valid_format_key = "r2gc-" + "A" * 59
    
    with pytest.raises(InvalidAPIKeyError):
        extract_api_key(valid_format_key)


def test_verify_api_key_none():
    """测试None密钥验证"""
    assert verify_api_key(None) is False


def test_verify_api_key_empty():
    """测试空密钥验证"""
    assert verify_api_key("") is False


def test_verify_api_key_invalid_format():
    """测试格式无效的密钥验证"""
    invalid_key = "invalid-key"
    assert verify_api_key(invalid_key) is False


def test_verify_api_key_with_valid_hash():
    """测试使用有效哈希的密钥验证"""
    from release2gitcode.core.config import settings
    from release2gitcode.core.security import _get_api_key_hash_bytes
    
    valid_key = "r2gc-" + "A" * 59
    hashed = bcrypt.hashpw(valid_key.encode("utf-8"), bcrypt.gensalt())
    
    original_hash = settings.api_key_hash
    settings.api_key_hash = hashed.decode("utf-8")
    _get_api_key_hash_bytes.cache_clear()
    
    try:
        assert verify_api_key(valid_key) is True
    finally:
        settings.api_key_hash = original_hash
        _get_api_key_hash_bytes.cache_clear()


def test_verify_api_key_with_wrong_key():
    """测试使用错误密钥的验证"""
    from release2gitcode.core.config import settings
    
    correct_key = "r2gc-" + "A" * 59
    wrong_key = "r2gc-" + "B" * 59
    hashed = bcrypt.hashpw(correct_key.encode("utf-8"), bcrypt.gensalt())
    
    original_hash = settings.api_key_hash
    settings.api_key_hash = hashed.decode("utf-8")
    
    try:
        assert verify_api_key(wrong_key) is False
    finally:
        settings.api_key_hash = original_hash
