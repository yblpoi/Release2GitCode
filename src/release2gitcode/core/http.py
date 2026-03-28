"""Shared HTTP client construction."""

from __future__ import annotations

import asyncio
import random
import time

import httpx

from release2gitcode.core.config import settings


def build_async_client() -> httpx.AsyncClient:
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive_connections,
    )
    timeout = httpx.Timeout(
        timeout=settings.http_timeout_seconds,
        connect=settings.http_connect_timeout_seconds,
        read=settings.http_read_timeout_seconds,
        write=settings.http_write_timeout_seconds,
        pool=settings.http_pool_timeout_seconds,
    )
    return httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)


def compute_github_backoff_seconds(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass

    rate_limit_reset = response.headers.get("X-RateLimit-Reset")
    if rate_limit_reset:
        try:
            reset_epoch = float(rate_limit_reset)
            return max(reset_epoch - time.time(), 0.0)
        except ValueError:
            pass

    exponential = settings.github_backoff_base_seconds * (2 ** max(attempt - 1, 0))
    jitter = random.uniform(0, 0.5)
    return min(exponential + jitter, settings.github_backoff_max_seconds)


async def sleep_for_github_backoff(response: httpx.Response, attempt: int) -> None:
    await asyncio.sleep(compute_github_backoff_seconds(response, attempt))
