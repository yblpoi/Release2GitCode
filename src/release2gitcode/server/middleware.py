"""Server middleware."""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from release2gitcode.core.config import settings
from release2gitcode.core.errors import HTTPSRequiredError


class HTTPSCheckMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, require_https: bool = settings.require_https) -> None:
        super().__init__(app)
        self.require_https = require_https

    async def dispatch(self, request: Request, call_next: Callable):
        if not self.require_https:
            return await call_next(request)
        if request.headers.get("X-Forwarded-Proto") == "https" or request.url.scheme == "https":
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
