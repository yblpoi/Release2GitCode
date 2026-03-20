"""Release2GitCode API Server

FastAPI 应用入口
- 统一错误处理
- 添加中间件
- 初始化安全组件
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.sync import router as sync_router
from app.api.middleware import HTTPSCheckMiddleware
from app.core.crypto import get_rsa_key_manager
from app.core.logger import get_security_logger
from app.config.settings import settings
from app.exceptions.errors import AppError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期处理

    启动时初始化 RSA 密钥并记录日志
    """

    rsa_manager = get_rsa_key_manager()
    logger = get_security_logger()
    logger.log_key_generated(rsa_manager.get_key_id())
    yield


app = FastAPI(
    title="Release2GitCode API",
    description="API 服务器，用于将 GitHub Release 同步到 GitCode Release",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(HTTPSCheckMiddleware, require_https=settings.require_https)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """统一处理应用自定义异常"""

    request_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            }
        },
    )


app.include_router(auth_router)
app.include_router(sync_router)


@app.get("/")
async def root() -> dict:
    """健康检查"""

    return {
        "status": "ok",
        "service": "Release2GitCode API",
        "version": "2.0.0",
    }


@app.get("/health")
async def health() -> dict:
    """健康检查"""

    return {"status": "healthy"}
