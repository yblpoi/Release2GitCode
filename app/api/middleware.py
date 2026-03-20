"""限流中间件和 HTTPS 检查中间件"""

import uuid
from typing import Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config.settings import settings
from app.core.logger import get_security_logger
from app.exceptions.errors import HTTPSRequiredError, RateLimitExceeded


class HTTPSCheckMiddleware(BaseHTTPMiddleware):
    """HTTPS 检查中间件

    如果配置 REQUIRE_HTTPS=true，则检查请求是否通过 HTTPS
    通过 X-Forwarded-Proto 头检查（由反向代理设置）
    """

    def __init__(
        self,
        app: ASGIApp,
        require_https: bool = settings.require_https,
    ) -> None:
        super().__init__(app)
        self.require_https = require_https

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> ASGIApp:
        if not self.require_https:
            return await call_next(request)

        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        if forwarded_proto == "https":
            return await call_next(request)

        if request.url.scheme == "https":
            return await call_next(request)

        error = HTTPSRequiredError()
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "request_id": str(uuid.uuid4()),
                }
            },
        )


class InMemoryRateLimiter:
    """内存限流器

    基于 IP + API 密钥计数限流
    """

    def __init__(self) -> None:
        self._requests: dict[str, deque[datetime]] = defaultdict(deque)

    def _cleanup_expired(self, key: str, window_seconds: int) -> None:
        """清理过期记录"""

        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        requests = self._requests[key]
        while requests and requests[0] <= cutoff:
            requests.popleft()

    def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int = 60
    ) -> bool:
        """检查是否超限，并增加计数

        Returns:
            True: 允许请求
            False: 超限
        """

        self._cleanup_expired(key, window_seconds)
        current_count = len(self._requests[key])

        if current_count >= max_requests:
            return False

        self._requests[key].append(datetime.utcnow())
        return True


_rate_limiter_instance: InMemoryRateLimiter | None = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """获取限流器单例"""

    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = InMemoryRateLimiter()
    return _rate_limiter_instance


def get_rate_limit_key(
    client_ip: str,
    api_key: str | None,
    endpoint: str,
) -> str:
    """生成限流键

    优先使用 API 密钥（如果有），否则使用 IP
    """

    if api_key:
        prefix = api_key[:8]
        return f"{prefix}:{endpoint}"

    return f"{client_ip}:{endpoint}"
