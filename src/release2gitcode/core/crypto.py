"""RSA key management."""

from __future__ import annotations

import base64
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from release2gitcode.core.errors import CryptoGenerationError, TokenDecryptionError


class RSAKeyManager:
    def __init__(self, key_size: int = 4096) -> None:
        self._key_id = str(uuid.uuid4())
        try:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend(),
            )
        except Exception as exc:
            raise CryptoGenerationError(str(exc)) from exc
        self._public_key = self._private_key.public_key()

    def get_key_id(self) -> str:
        return self._key_id

    def get_public_key_pem(self) -> str:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def decrypt(self, encrypted_data_b64: str) -> str:
        try:
            encrypted_data = base64.b64decode(encrypted_data_b64)
            plaintext = self._private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except Exception as exc:
            raise TokenDecryptionError() from exc
        return plaintext.decode("utf-8")


_instance: RSAKeyManager | None = None


def get_rsa_key_manager() -> RSAKeyManager:
    global _instance
    if _instance is None:
        _instance = RSAKeyManager()
    return _instance
