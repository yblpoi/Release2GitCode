"""RSA 加密/解密管理器

- 服务器启动时生成 4096 位 RSA 密钥对
- 密钥仅存在于内存中，重启后自动重新生成
- 提供公钥获取接口和私钥解密接口
"""

import uuid
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

from app.exceptions.errors import CryptoGenerationError, TokenDecryptionError


class RSAKeyManager:
    """RSA 密钥管理器"""

    def __init__(self, key_size: int = 4096) -> None:
        """初始化并生成新的 RSA 密钥对"""

        self._private_key: rsa.RSAPrivateKey
        self._public_key: rsa.RSAPublicKey
        self._key_id: str = str(uuid.uuid4())

        try:
            self._generate_keys(key_size)
        except Exception as e:
            raise CryptoGenerationError(f"Failed to generate RSA keys: {str(e)}") from e

    def _generate_keys(self, key_size: int) -> None:
        """生成新的 RSA 密钥对"""

        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

    def get_key_id(self) -> str:
        """获取当前密钥 ID"""

        return self._key_id

    def get_public_key_pem(self) -> str:
        """获取 PEM 格式的公钥"""

        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def decrypt(self, encrypted_data_b64: str) -> str:
        """使用私钥解密 base64 编码的数据

        Args:
            encrypted_data_b64: base64 编码的加密数据

        Returns:
            解密后的明文字符串

        Raises:
            TokenDecryptionError: 解密失败
        """

        import base64

        try:
            encrypted_data = base64.b64decode(encrypted_data_b64)
            plaintext = self._private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return plaintext.decode('utf-8')
        except (ValueError, TypeError, base64.binascii.Error) as e:
            raise TokenDecryptionError() from e


_instance: RSAKeyManager | None = None


def get_rsa_key_manager() -> RSAKeyManager:
    """获取单例 RSA 密钥管理器实例"""

    global _instance
    if _instance is None:
        _instance = RSAKeyManager()
    return _instance
