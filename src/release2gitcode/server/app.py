"""ASGI application factory."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from release2gitcode.core.crypto import get_rsa_key_manager
from release2gitcode.core.errors import AppError
from release2gitcode.core.logger import get_security_logger
from release2gitcode.core.models import GetPublicKeyResponse, SyncRequest, SyncResponse
from release2gitcode.core.security import extract_api_key
from release2gitcode.core.sync import ReleaseSyncService
from release2gitcode.server.middleware import HTTPSCheckMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    rsa_manager = get_rsa_key_manager()
    get_security_logger().log_key_generated(rsa_manager.get_key_id())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Release2GitCode API",
        description="Sync GitHub Releases to GitCode through a secured API.",
        version="3.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(HTTPSCheckMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": str(uuid.uuid4()),
                }
            },
        )

    router = APIRouter(prefix="/api/v1")
    sync_service = ReleaseSyncService()

    @router.get("/public-key", response_model=GetPublicKeyResponse, tags=["auth"])
    async def get_public_key(request: Request) -> GetPublicKeyResponse:
        request_id = str(uuid.uuid4())
        client_ip = request.client.host if request.client else "unknown"
        api_key = extract_api_key(request.headers.get("X-API-Key"))
        rsa_manager = get_rsa_key_manager()
        get_security_logger().log_public_key_request(request_id, client_ip, api_key)
        return GetPublicKeyResponse(public_key=rsa_manager.get_public_key_pem(), key_id=rsa_manager.get_key_id())

    @router.post("/sync", response_model=SyncResponse, tags=["sync"])
    async def sync_release(request: Request, payload: SyncRequest) -> SyncResponse:
        task_id = str(uuid.uuid4())
        client_ip = request.client.host if request.client else "unknown"
        api_key = extract_api_key(request.headers.get("X-API-Key"))
        logger = get_security_logger()
        github_url = str(payload.github_release_url)
        gitcode_url = str(payload.gitcode_repo_url)
        logger.log_sync_started(task_id, client_ip, api_key, github_url, gitcode_url)

        rsa_manager = get_rsa_key_manager()
        try:
            gitcode_token = rsa_manager.decrypt(payload.encrypted_gitcode_token)
            GH_TOKEN = rsa_manager.decrypt(payload.encrypted_GH_TOKEN) if payload.encrypted_GH_TOKEN else None
            sendkey = rsa_manager.decrypt(payload.encrypted_serverchan3_sendkey) if payload.encrypted_serverchan3_sendkey else None
        except AppError as exc:
            logger.log_token_decrypt_failed(task_id, client_ip, api_key, exc.message)
            raise

        async def run_sync_in_background() -> None:
            try:
                result = await sync_service.sync_github_release(
                    github_release_url=github_url,
                    gitcode_repo_url=gitcode_url,
                    gitcode_token=gitcode_token,
                    GH_TOKEN=GH_TOKEN,
                    task_id=task_id,
                    serverchan3_sendkey=sendkey,
                )
            except AppError as exc:
                logger.log_sync_failed(task_id, client_ip, api_key, exc.message)
                return
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.log_sync_failed(task_id, client_ip, api_key, str(exc))
                return

            logger.log_sync_completed(
                task_id,
                client_ip,
                api_key,
                result.total_assets,
                result.processed_assets,
                result.skipped_assets,
                len(result.failed_assets),
                result.duration_seconds,
                result.notification_warning,
            )

        asyncio.create_task(run_sync_in_background())
        return SyncResponse(
            task_id=task_id,
            status="accepted",
            message="Synchronization task accepted and running in background.",
            processed_assets=0,
            skipped_assets=0,
            failed_assets=[],
        )

    app.include_router(router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok", "service": "Release2GitCode API", "version": "3.0.0"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    return app


app = create_app()
