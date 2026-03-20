"""认证相关 API：获取公钥端点"""

import uuid
from fastapi import APIRouter, Request

from app.core.crypto import get_rsa_key_manager
from app.core.security import extract_api_key
from app.core.logger import get_security_logger
from app.models.schemas import GetPublicKeyResponse

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/public-key", response_model=GetPublicKeyResponse)
async def get_public_key(request: Request) -> GetPublicKeyResponse:
    """获取当前服务器 RSA 公钥

    需要提供有效的 API 密钥（X-API-Key 请求头）
    """

    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    api_key = extract_api_key(request.headers.get("X-API-Key"))

    rsa_manager = get_rsa_key_manager()

    logger = get_security_logger()
    logger.log_public_key_request(
        request_id=request_id,
        client_ip=client_ip,
        api_key=api_key,
        success=True,
    )

    return GetPublicKeyResponse(
        public_key=rsa_manager.get_public_key_pem(),
        key_id=rsa_manager.get_key_id(),
    )
