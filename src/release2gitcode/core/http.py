"""Shared HTTP client construction."""

from __future__ import annotations

import httpx

from release2gitcode.core.config import settings


def build_async_client() -> httpx.AsyncClient:
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive_connections,
    )
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    return httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
