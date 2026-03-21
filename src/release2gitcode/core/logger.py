"""Structured security logging."""

from __future__ import annotations

import logging
from typing import Any

from pythonjsonlogger import jsonlogger

from release2gitcode.core.config import settings
from release2gitcode.core.security import get_api_key_hash_prefix


class SecurityLogger:
    def __init__(self, name: str = "security") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                jsonlogger.JsonFormatter(
                    "%(asctime)s %(levelname)s %(event_type)s %(request_id)s %(client_ip)s %(api_key_prefix)s %(success)s %(message)s"
                )
            )
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def _log(
        self,
        *,
        event_type: str,
        request_id: str,
        client_ip: str,
        success: bool,
        api_key: str | None = None,
        message: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        api_key_prefix = get_api_key_hash_prefix(settings.api_key_hash) if api_key and settings.api_key_hash else ""
        payload = {
            "event_type": event_type,
            "request_id": request_id,
            "client_ip": client_ip,
            "api_key_prefix": api_key_prefix,
            "success": success,
            "message_text": message,
        }
        if extra:
            payload.update(extra)
        self._logger.info("", extra=payload)

    def log_key_generated(self, key_id: str, key_size: int = 4096) -> None:
        self._log(
            event_type="key_generated",
            request_id="-",
            client_ip="-",
            success=True,
            message=f"RSA key pair generated, key_id={key_id}, size={key_size}",
            extra={"key_id": key_id, "key_size": key_size},
        )

    def log_public_key_request(self, request_id: str, client_ip: str, api_key: str) -> None:
        self._log(event_type="public_key_requested", request_id=request_id, client_ip=client_ip, success=True, api_key=api_key)

    def log_token_decrypt_failed(self, request_id: str, client_ip: str, api_key: str, error: str) -> None:
        self._log(
            event_type="token_decrypt_failed",
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            api_key=api_key,
            message=error,
        )

    def log_sync_started(self, request_id: str, client_ip: str, api_key: str, github_url: str, gitcode_url: str) -> None:
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
        self,
        request_id: str,
        client_ip: str,
        api_key: str,
        total_assets: int,
        processed: int,
        skipped: int,
        failed: int,
        duration_seconds: float,
        notification_warning: str | None = None,
    ) -> None:
        self._log(
            event_type="sync_completed",
            request_id=request_id,
            client_ip=client_ip,
            success=failed == 0,
            api_key=api_key,
            message=f"Synchronization completed in {duration_seconds:.2f}s",
            extra={
                "total_assets": total_assets,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "duration_seconds": duration_seconds,
                "notification_warning": notification_warning or "",
            },
        )

    def log_sync_failed(self, request_id: str, client_ip: str, api_key: str, error: str) -> None:
        self._log(
            event_type="sync_failed",
            request_id=request_id,
            client_ip=client_ip,
            success=False,
            api_key=api_key,
            message=error,
        )


_logger: SecurityLogger | None = None


def get_security_logger() -> SecurityLogger:
    global _logger
    if _logger is None:
        _logger = SecurityLogger()
    return _logger
