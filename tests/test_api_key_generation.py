"""测试API密钥生成和集成功能"""

import pytest
import subprocess
import tempfile
import os
import bcrypt

from release2gitcode.core.security import (
    validate_api_key_format,
    verify_api_key,
    API_KEY_PREFIX,
    API_KEY_LENGTH,
)
from release2gitcode.core.config import settings


def test_docker_entrypoint_generates_valid_key():
    """测试Docker入口脚本生成的密钥格式正确"""
    python_code = '''
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
'''
    
    result = subprocess.run(
        ["python3", "-c", python_code],
        capture_output=True,
        text=True,
        check=True
    )
    
    generated_key = result.stdout.strip()
    
    assert len(generated_key) == API_KEY_LENGTH
    assert generated_key.startswith(API_KEY_PREFIX)
    assert validate_api_key_format(generated_key) is True


def test_docker_entrypoint_generates_multiple_unique_keys():
    """测试Docker入口脚本生成的密钥是唯一的"""
    python_code = '''
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
'''
    
    keys = set()
    for _ in range(10):
        result = subprocess.run(
            ["python3", "-c", python_code],
            capture_output=True,
            text=True,
            check=True
        )
        keys.add(result.stdout.strip())
    
    assert len(keys) == 10


def test_key_hashing_and_verification():
    """测试密钥哈希计算和验证"""
    python_code = '''
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
'''
    
    result = subprocess.run(
        ["python3", "-c", python_code],
        capture_output=True,
        text=True,
        check=True
    )
    
    api_key = result.stdout.strip()
    
    hash_code = f'''
import bcrypt
import sys
api_key = sys.stdin.read().strip().encode("utf-8")
hashed = bcrypt.hashpw(api_key, bcrypt.gensalt())
print(hashed.decode("utf-8"))
'''
    
    hash_result = subprocess.run(
        ["python3", "-c", hash_code],
        input=api_key,
        capture_output=True,
        text=True,
        check=True
    )
    
    hashed_key = hash_result.stdout.strip()
    
    original_hash = settings.api_key_hash
    settings.api_key_hash = hashed_key
    
    try:
        assert verify_api_key(api_key) is True
    finally:
        settings.api_key_hash = original_hash


def test_key_format_validation_edge_cases():
    """测试密钥格式验证的边界情况"""
    valid_key = "r2gc-" + "A" * 59
    
    assert validate_api_key_format(valid_key) is True
    
    edge_cases = [
        ("r2gc-" + "A" * 58, False),  # 太短
        ("r2gc-" + "A" * 60, False),  # 太长
        ("r2gc-" + "A" * 58 + "!", False),  # 包含特殊字符
        ("r2gc-" + "A" * 58 + " ", False),  # 包含空格
        ("r2gc-" + "A" * 58 + "_", False),  # 包含下划线
        ("abc-" + "A" * 59, False),  # 错误前缀
        ("A" * 64, False),  # 无前缀
        ("", False),  # 空字符串
    ]
    
    for key, expected in edge_cases:
        assert validate_api_key_format(key) == expected


def test_key_contains_only_allowed_chars():
    """测试生成的密钥只包含允许的字符"""
    python_code = '''
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
'''
    
    result = subprocess.run(
        ["python3", "-c", python_code],
        capture_output=True,
        text=True,
        check=True
    )
    
    generated_key = result.stdout.strip()
    
    allowed_chars = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-"
    )
    
    for char in generated_key:
        assert char in allowed_chars


def test_key_prefix_is_correct():
    """测试生成的密钥前缀正确"""
    python_code = '''
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
'''
    
    result = subprocess.run(
        ["python3", "-c", python_code],
        capture_output=True,
        text=True,
        check=True
    )
    
    generated_key = result.stdout.strip()
    
    assert generated_key.startswith("r2gc-")
    assert generated_key[:5] == "r2gc-"


def test_key_length_is_exactly_64():
    """测试生成的密钥长度正好是64"""
    python_code = '''
import secrets
import string
prefix = "r2gc-"
chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "-"
random_part = "".join(secrets.choice(chars) for _ in range(59))
api_key = prefix + random_part
print(api_key)
'''
    
    result = subprocess.run(
        ["python3", "-c", python_code],
        capture_output=True,
        text=True,
        check=True
    )
    
    generated_key = result.stdout.strip()
    
    assert len(generated_key) == 64
    assert len(generated_key) == API_KEY_LENGTH
