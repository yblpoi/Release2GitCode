"""安全日志记录器

记录关键安全事件：
- 密钥生成事件
- API 访问日志
- 令牌验证失败日志
- 限流触发日志
- 同步任务开始/完成/失败日志
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from pythonjsonlogger import jsonlogger

from app.config.settings import settings
from app.core.security import get_api_key_hash_prefix


class SecurityLogger:
    """安全日志记录器"""

    def __init__(self, name: str = "security") -> None:
        self._logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """设置 JSON 格式日志"""

        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(event_type)s %(request_id)s %(client_ip)s %(api_key_prefix)s %(success)s %(message)s"
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def _log(
        self,
        event_type: str,
        request_id: str,
        client_ip: str,
        success: bool,
        api_key: Optional[str] = None,
        message: str = "",
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """输出 JSON 结构化日志"""

        api_key_prefix = ""
        if api_key and settings.api_key_hash:
            api_key_prefix = get_api_key_hash_prefix(settings.api_key_hash)

        log_data = {
            "event_type": event_type,
            "request_id": request_id,
            "client_ip": client_ip,
            "api_key_prefix": api_key_prefix,
            "success": success,
            "message_text": message,
        }
        if extra:
            log_data.update(extra)

        self._logger.info("", extra=log_data)

    def log_key_generated(
        self, key_id: str, key_size: int = 4096
    ) -> None:
        """记录密钥生成事件"""

        self._log(
            event_type="key_generated",
            request_id="-",
            client_ip="-",
            success=True,
            message=f"RSA key pair generated, key_id={key_id}, size={key_size}",
            extra={"key_id": key_id, "key_size": key_size},
        )

    def log_public_key_request(
        self, request_id: str, client_ip: str, api_key: str, success: bool, error: str = ""
    ) -> None:
        """记录公钥请求"""

        self._log(
            event_type="public_key_requested",
            request_id=request_id,
            client_ip=client_ip,
            success=success,
            api_key=api_key,
            message=error,
        )

    def log_token_decrypt_failed(
        self, request_id: str, client_ip: str, api_key: str, error: str = ""
    ) -> None:
        """记录令牌解密失败"""

        self._log(
            event_type="token_decrypt_failed",
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            api_key=api_key,
            message=error,
        )

    def log_rate_limit_exceeded(
        self, request_id: str, client_ip: str, api_key: str | None, endpoint: str
    ) -> None:
        """记录限流触发"""

        self._log(
            event_type="rate_limit_exceeded",
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            api_key=api_key,
            message=f"Rate limit exceeded on {endpoint}",
            extra={"endpoint": endpoint},
        )

    def log_sync_started(
        self, request_id: str, client_ip: str, api_key: str, github_url: str, gitcode_url: str
    ) -> None:
        """记录同步开始"""

        self._log(
            event_type="sync_started",
            request_id=request_id,
            client_ip=client_ip,
            success=True,
            api_key=api_key,
            message=f"Synchronization started: {github_url} -> {gitcode_url}",
            extra={"github_url": github_url, "gitcode_url": gitcode_url},
        )

    def log_sync_completed(
        self, request_id: str, client_ip: str, api_key: str,
        total_assets: int, processed: int, skipped: int, failed: int,
        duration_seconds: float
    ) -> None:
        """记录同步完成"""

        self._log(
            event_type="sync_completed",
            request_id=request_id,
            client_ip=client_ip,
            success=True,
            api_key=api_key,
            message=f"Synchronization completed in {duration_seconds:.2f}s",
            extra={
                "total_assets": total_assets,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "duration_seconds": duration_seconds,
            },
        )

    def log_sync_failed(
        self, request_id: str, client_ip: str, api_key: str, error: str
    ) -> None:
        """记录同步失败"""

        self._log(
            event_type="sync_failed",
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            api_key=api_key,
            message=error,
        )


_security_logger_instance: SecurityLogger | None = None


def get_security_logger() -> SecurityLogger:
    """获取安全日志记录器单例"""

    global _security_logger_instance
    if _security_logger_instance is None:
        _security_logger_instance = SecurityLogger()
    return _security_logger_instance
