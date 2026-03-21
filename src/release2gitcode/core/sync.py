"""Shared release synchronization workflows."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import AsyncIterator

from release2gitcode.core.config import discover_default_assets, getenv_str, parse_multiline_files_env, settings
from release2gitcode.core.github import get_release_info, parse_github_release_url
from release2gitcode.core.gitcode import GitCodeReleaseClient, parse_gitcode_repo_url
from release2gitcode.core.http import build_async_client
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

            processed = 0
            skipped = 0
            failed_assets: list[str] = []

            for asset in release_info.assets:
                if asset.name in existing_assets:
                    skipped += 1
                    continue
                if await self._upload_github_asset(gitcode=gitcode, tag=release_info.tag_name, asset=asset):
                    processed += 1
                    existing_assets.add(asset.name)
                else:
                    failed_assets.append(asset.name)

            result = SyncResult(
                task_id=task_id,
                github_release_url=github_release_url,
                gitcode_repo_url=gitcode_ref.repo_url,
                processed_assets=processed,
                skipped_assets=skipped,
                failed_assets=failed_assets,
                total_assets=len(release_info.assets),
                duration_seconds=time.time() - start_time,
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
                github_release_url="",
                gitcode_repo_url=gitcode_ref.repo_url,
                processed_assets=processed,
                skipped_assets=skipped,
                failed_assets=[],
                total_assets=len(config.files),
                duration_seconds=time.time() - start_time,
            )

    async def _upload_github_asset(self, *, gitcode: GitCodeReleaseClient, tag: str, asset: GitHubAsset) -> bool:
        async def stream_factory() -> AsyncIterator[bytes]:
            async with gitcode.client.stream("GET", asset.browser_download_url) as response:
                if response.status_code >= 400:
                    raise RuntimeError(f"Download failed for {asset.name}: HTTP {response.status_code}")
                async for chunk in response.aiter_bytes(chunk_size=settings.chunk_size):
                    yield chunk

        try:
            await gitcode.upload_stream(
                tag,
                asset,
                stream_factory,
                upload_attempts=settings.upload_attempts,
                timeout_seconds=None,
            )
            return True
        except Exception:
            return False


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
