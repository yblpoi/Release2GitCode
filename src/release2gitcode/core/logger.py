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

    def log_asset_transfer(
        self,
        request_id: str,
        *,
        asset_name: str,
        phase: str,
        bytes_total: int | None,
        duration_seconds: float,
        throughput_mbps: float | None,
        attempt: int | None = None,
    ) -> None:
        bytes_human = f"{bytes_total} bytes" if bytes_total is not None else "unknown"
        speed_human = f"{throughput_mbps:.2f} MB/s" if throughput_mbps is not None else "unknown"
        self._log(
            event_type="asset_transfer",
            request_id=request_id,
            client_ip="-",
            success=True,
            message=(
                f"{phase} finished for {asset_name}: size={bytes_human}, duration={duration_seconds:.2f}s, "
                f"throughput={speed_human}"
            ),
            extra={
                "asset_name": asset_name,
                "phase": phase,
                "bytes_total": bytes_total,
                "duration_seconds": duration_seconds,
                "throughput_mbps": throughput_mbps,
                "attempt": attempt,
            },
        )

    def log_server_boot(self) -> None:
        self._log(
            event_type="server_boot",
            request_id="-",
            client_ip="-",
            success=True,
            message="Release2GitCode API server boot completed",
            extra={
                "require_https": settings.require_https,
                "http_timeout_seconds": settings.http_timeout_seconds,
                "http_max_connections": settings.http_max_connections,
                "http_max_keepalive_connections": settings.http_max_keepalive_connections,
                "chunk_size": settings.chunk_size,
                "upload_attempts": settings.upload_attempts,
                "sync_concurrency": settings.sync_concurrency,
                "server_log_level": settings.server_log_level,
                "server_access_log": settings.server_access_log,
            },
        )

    def log_sync_progress(
        self,
        request_id: str,
        *,
        asset_name: str,
        asset_status: str,
        asset_index: int,
        total_assets: int,
        completed_assets: int,
        remaining_assets: int,
        processed_assets: int,
        skipped_assets: int,
        failed_assets: int,
        elapsed_seconds: float,
        estimated_remaining_seconds: float,
    ) -> None:
        elapsed_human = self._format_duration(elapsed_seconds)
        eta_human = self._format_duration(estimated_remaining_seconds)
        self._log(
            event_type="sync_progress",
            request_id=request_id,
            client_ip="-",
            success=asset_status != "failed",
            message=(
                f"Asset {asset_status}: [{asset_index}/{total_assets}] {asset_name}; "
                f"completed={completed_assets}/{total_assets}, "
                f"remaining={remaining_assets}, "
                f"elapsed={elapsed_human}, "
                f"eta={eta_human}"
            ),
            extra={
                "asset_name": asset_name,
                "asset_status": asset_status,
                "asset_index": asset_index,
                "total_assets": total_assets,
                "completed_assets": completed_assets,
                "remaining_assets": remaining_assets,
                "processed_assets": processed_assets,
                "skipped_assets": skipped_assets,
                "failed_assets": failed_assets,
                "elapsed_seconds": elapsed_seconds,
                "elapsed_human": elapsed_human,
                "estimated_remaining_seconds": estimated_remaining_seconds,
                "estimated_remaining_human": eta_human,
            },
        )

    def log_permission_check(
        self,
        request_id: str,
        *,
        repo: str,
        tag: str,
        permission_check_result: str,
        success: bool,
        detail: str = "",
    ) -> None:
        self._log(
            event_type="permission_check",
            request_id=request_id,
            client_ip="-",
            success=success,
            message=detail or f"Permission check {permission_check_result} for {repo}@{tag}",
            extra={
                "repo": repo,
                "tag": tag,
                "permission_check_result": permission_check_result,
            },
        )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(int(round(seconds)), 0)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

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
