"""同步 API：GitHub Release 同步到 GitCode"""

import uuid
import time
from typing import List

from fastapi import APIRouter, Request

from app.core.crypto import get_rsa_key_manager
from app.core.security import extract_api_key
from app.core.logger import get_security_logger
from app.core.github import parse_github_release_url, get_release_info
from app.services.downloader import StreamDownloader
from app.services.uploader import GitCodeStreamUploader, parse_gitcode_repo_url
from app.models.schemas import SyncRequest, SyncResponse, GitHubReleaseInfo
from app.exceptions.errors import TokenDecryptionError

router = APIRouter(prefix="/api/v1", tags=["sync"])


@router.post("/sync", response_model=SyncResponse)
async def sync_release(request: Request, sync_request: SyncRequest) -> SyncResponse:
    """同步 GitHub Release 到 GitCode Release

    流程：
    1. 解密 GitCode 令牌
    2. 获取 GitHub Release 信息
    3. 确保 GitCode Release 存在
    4. 逐个流式下载并上传每个 asset
    """

    task_id = str(uuid.uuid4())
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    api_key = extract_api_key(request.headers.get("X-API-Key"))
    logger = get_security_logger()

    github_url = str(sync_request.github_release_url)
    gitcode_url = str(sync_request.gitcode_repo_url)

    logger.log_sync_started(
        request_id=task_id,
        client_ip=client_ip,
        api_key=api_key,
        github_url=github_url,
        gitcode_url=gitcode_url,
    )

    try:
        rsa_manager = get_rsa_key_manager()
        gitcode_token = rsa_manager.decrypt(sync_request.encrypted_gitcode_token)
    except TokenDecryptionError as e:
        logger.log_token_decrypt_failed(
            request_id=task_id,
            client_ip=client_ip,
            api_key=api_key,
            error=str(e),
        )
        raise

    owner, repo, tag = parse_github_release_url(github_url)
    gitcode_owner, gitcode_repo = parse_gitcode_repo_url(gitcode_url)

    release_info = await get_release_info(owner, repo, tag)

    uploader = GitCodeStreamUploader(
        token=gitcode_token,
        owner=gitcode_owner,
        repo=gitcode_repo,
        tag=release_info.tag_name,
    )

    release = await uploader.ensure_release(
        name=release_info.name,
        body=release_info.body,
    )

    existing_assets = uploader.get_existing_asset_names(release)

    processed = 0
    skipped = 0
    failed_assets: List[str] = []

    for asset in release_info.assets:
        if asset.name in existing_assets:
            skipped += 1
            continue

        downloader = StreamDownloader(asset)
        success = await uploader.upload_stream(asset, downloader)
        if success:
            processed += 1
        else:
            failed_assets.append(asset.name)

    duration = time.time() - start_time
    total_assets = len(release_info.assets)

    logger.log_sync_completed(
        request_id=task_id,
        client_ip=client_ip,
        api_key=api_key,
        total_assets=total_assets,
        processed=processed,
        skipped=skipped,
        failed=len(failed_assets),
        duration_seconds=duration,
    )

    return SyncResponse(
        task_id=task_id,
        status="completed",
        message=f"Synchronization completed. Processed {processed} assets, skipped {skipped}, failed {len(failed_assets)}.",
        processed_assets=processed,
        skipped_assets=skipped,
        failed_assets=failed_assets,
    )
