"""Shared release synchronization workflows."""

from __future__ import annotations

import os
import time
import uuid
import asyncio
from asyncio import Lock, Semaphore
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncIterator

from release2gitcode.core.config import discover_default_assets, getenv_str, parse_multiline_files_env, settings
from release2gitcode.core.github import get_release_info, parse_github_release_url
from release2gitcode.core.gitcode import GitCodeReleaseClient, parse_gitcode_repo_url
from release2gitcode.core.http import build_async_client, sleep_for_github_backoff
from release2gitcode.core.logger import get_security_logger
from release2gitcode.core.models import GitHubAsset, LocalUploadConfig, SyncResult
from release2gitcode.core.notifications import send_serverchan_notification


class ReleaseSyncService:
    async def sync_github_release(
        self,
        *,
        github_release_url: str,
        gitcode_repo_url: str,
        gitcode_token: str,
        GH_TOKEN: str | None = None,
        task_id: str | None = None,
        serverchan3_sendkey: str | None = None,
    ) -> SyncResult:
        task_id = task_id or str(uuid.uuid4())
        start_time = time.time()
        triggered_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        logger = get_security_logger()
        owner, repo, tag = parse_github_release_url(github_release_url)
        gitcode_ref = parse_gitcode_repo_url(gitcode_repo_url)

        async with build_async_client() as client:
            release_info = await get_release_info(
                client,
                settings.github_api_base,
                owner,
                repo,
                tag,
                GH_TOKEN=GH_TOKEN,
            )
            gitcode = GitCodeReleaseClient(client, gitcode_token, gitcode_ref.owner, gitcode_ref.repo)
            release = await gitcode.ensure_release(release_info.tag_name, release_info.name, release_info.body)
            existing_assets = gitcode.get_existing_asset_names(release)
            total_assets = len(release_info.assets)

            processed = 0
            skipped = 0
            total_bytes = 0
            failed_assets: list[str] = []
            progress_lock = Lock()
            semaphore = Semaphore(max(1, settings.sync_concurrency))
            github_headers = {
                "Accept": "application/octet-stream, */*",
                "User-Agent": settings.github_download_user_agent,
                "Connection": "keep-alive",
            }
            if GH_TOKEN:
                github_headers["Authorization"] = f"Bearer {GH_TOKEN}"

            async def handle_asset(asset_index: int, asset: GitHubAsset) -> None:
                nonlocal processed, skipped, total_bytes
                if asset.name in existing_assets:
                    async with progress_lock:
                        skipped += 1
                        self._log_progress(
                            logger=logger,
                            task_id=task_id,
                            asset_name=asset.name,
                            asset_status="skipped",
                            asset_index=asset_index,
                            processed=processed,
                            skipped=skipped,
                            failed=len(failed_assets),
                            total_assets=total_assets,
                            start_time=start_time,
                        )
                    return

                async with semaphore:
                    uploaded = await self._upload_github_asset(
                        gitcode=gitcode,
                        tag=release_info.tag_name,
                        asset=asset,
                        task_id=task_id,
                        github_headers=github_headers,
                    )

                async with progress_lock:
                    if uploaded:
                        processed += 1
                        total_bytes += asset.size
                        existing_assets.add(asset.name)
                        status = "completed"
                    else:
                        failed_assets.append(asset.name)
                        status = "failed"
                    self._log_progress(
                        logger=logger,
                        task_id=task_id,
                        asset_name=asset.name,
                        asset_status=status,
                        asset_index=asset_index,
                        processed=processed,
                        skipped=skipped,
                        failed=len(failed_assets),
                        total_assets=total_assets,
                        start_time=start_time,
                    )

            await asyncio.gather(
                *(handle_asset(asset_index, asset) for asset_index, asset in enumerate(release_info.assets, start=1))
            )

            result = SyncResult(
                task_id=task_id,
                triggered_at=triggered_at,
                github_release_url=github_release_url,
                gitcode_repo_url=gitcode_ref.repo_url,
                processed_assets=processed,
                skipped_assets=skipped,
                failed_assets=failed_assets,
                total_assets=total_assets,
                duration_seconds=time.time() - start_time,
                total_bytes=total_bytes,
            )
            if serverchan3_sendkey:
                try:
                    await send_serverchan_notification(client, serverchan3_sendkey, result)
                except Exception as exc:
                    result.notification_warning = str(exc)
            return result

    async def upload_local_release(self, config: LocalUploadConfig) -> SyncResult:
        task_id = str(uuid.uuid4())
        start_time = time.time()
        triggered_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        gitcode_ref = parse_gitcode_repo_url(config.repo_url)
        async with build_async_client() as client:
            gitcode = GitCodeReleaseClient(client, config.token, gitcode_ref.owner, gitcode_ref.repo)
            release = await gitcode.ensure_release(
                config.tag,
                config.release_name,
                config.release_body,
                target_branch=config.target_branch,
            )
            existing_assets = gitcode.get_existing_asset_names(release)
            processed = 0
            skipped = 0
            for path in config.files:
                if path.name in existing_assets:
                    skipped += 1
                    continue
                await gitcode.upload_bytes(config.tag, path, config.upload_attempts, config.timeout_seconds)
                processed += 1
                existing_assets.add(path.name)
            return SyncResult(
                task_id=task_id,
                triggered_at=triggered_at,
                github_release_url="",
                gitcode_repo_url=gitcode_ref.repo_url,
                processed_assets=processed,
                skipped_assets=skipped,
                failed_assets=[],
                total_assets=len(config.files),
                duration_seconds=time.time() - start_time,
            )

    async def _upload_github_asset(
        self,
        *,
        gitcode: GitCodeReleaseClient,
        tag: str,
        asset: GitHubAsset,
        task_id: str,
        github_headers: dict[str, str],
    ) -> bool:
        logger = get_security_logger()

        async def stream_factory() -> AsyncIterator[bytes]:
            response = None
            for attempt in range(1, settings.github_max_retries + 1):
                response = await gitcode.client.send(
                    gitcode.client.build_request("GET", asset.browser_download_url, headers=github_headers),
                    stream=True,
                )
                if response.status_code not in {403, 429} or attempt >= settings.github_max_retries:
                    break
                await response.aclose()
                await sleep_for_github_backoff(response, attempt)

            if response is None:
                raise RuntimeError(f"Download failed for {asset.name}: empty response")

            try:
                if response.status_code >= 400:
                    raise RuntimeError(f"Download failed for {asset.name}: HTTP {response.status_code}")
                async for chunk in response.aiter_bytes(chunk_size=settings.chunk_size):
                    yield chunk
            finally:
                await response.aclose()

        try:
            started_at = time.time()
            await gitcode.upload_stream(
                tag,
                asset,
                stream_factory,
                upload_attempts=settings.upload_attempts,
                timeout_seconds=None,
            )
            duration = time.time() - started_at
            throughput_mbps = asset.size / (1024 * 1024) / duration if asset.size > 0 and duration > 0 else None
            logger.log_asset_transfer(
                task_id,
                asset_name=asset.name,
                phase="download_and_upload",
                bytes_total=asset.size,
                duration_seconds=duration,
                throughput_mbps=throughput_mbps,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _log_progress(
        *,
        logger,
        task_id: str,
        asset_name: str,
        asset_status: str,
        asset_index: int,
        processed: int,
        skipped: int,
        failed: int,
        total_assets: int,
        start_time: float,
    ) -> None:
        completed = processed + skipped + failed
        remaining = max(total_assets - completed, 0)
        elapsed = time.time() - start_time
        average_seconds = elapsed / completed if completed else 0.0
        estimated_remaining_seconds = average_seconds * remaining if remaining else 0.0
        logger.log_sync_progress(
            task_id,
            asset_name=asset_name,
            asset_status=asset_status,
            asset_index=asset_index,
            total_assets=total_assets,
            completed_assets=completed,
            remaining_assets=remaining,
            processed_assets=processed,
            skipped_assets=skipped,
            failed_assets=failed,
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=estimated_remaining_seconds,
        )


def load_local_upload_config_from_env() -> LocalUploadConfig:
    timeout_raw = getenv_str("GITCODE_TIMEOUT")
    files_env = os.getenv("GITCODE_FILES", "")
    files = parse_multiline_files_env(files_env) if files_env else discover_default_assets(Path("release_assets"))
    return LocalUploadConfig(
        token=getenv_str("GITCODE_TOKEN"),
        repo_url=getenv_str("GITCODE_REPO_URL"),
        tag=getenv_str("GITCODE_TAG"),
        release_name=getenv_str("GITCODE_RELEASE_NAME") or None,
        release_body=os.getenv("GITCODE_RELEASE_BODY"),
        target_branch=getenv_str("GITCODE_TARGET_BRANCH") or None,
        upload_attempts=int(getenv_str("GITCODE_UPLOAD_ATTEMPTS") or str(settings.upload_attempts)),
        timeout_seconds=float(timeout_raw) if timeout_raw else None,
        files=files,
    )
