"""ServerChan3 notifications."""

from __future__ import annotations

import re

import httpx

from release2gitcode.core.errors import NetworkError
from release2gitcode.core.models import SyncResult


SENDKEY_UID_RE = re.compile(r"^sctp(\d+)t")


def extract_serverchan_uid(sendkey: str) -> str:
    match = SENDKEY_UID_RE.match(sendkey)
    if not match:
        raise ValueError("Unable to extract uid from ServerChan3 SendKey")
    return match.group(1)


def build_serverchan_payload(result: SyncResult) -> dict[str, str]:
    title = (
        f"Release2GitCode success: {result.processed_assets}/{result.total_assets}"
        if result.is_success
        else f"Release2GitCode partial failure: {len(result.failed_assets)} asset(s)"
    )
    failed_summary = ", ".join(result.failed_assets[:10]) or "None"
    desp = "\n".join(
        [
            f"Task ID: `{result.task_id}`",
            f"GitHub Release: {result.github_release_url}",
            f"GitCode Repo: {result.gitcode_repo_url}",
            f"Processed: {result.processed_assets}",
            f"Skipped: {result.skipped_assets}",
            f"Failed: {len(result.failed_assets)}",
            f"Failed Assets: {failed_summary}",
            f"Duration: {result.duration_seconds:.2f}s",
        ]
    )
    return {
        "title": title,
        "desp": desp,
        "short": f"processed={result.processed_assets}, skipped={result.skipped_assets}, failed={len(result.failed_assets)}",
        "tags": "release2gitcode|gitcode|sync",
    }


async def send_serverchan_notification(client: httpx.AsyncClient, sendkey: str, result: SyncResult) -> None:
    uid = extract_serverchan_uid(sendkey)
    url = f"https://{uid}.push.ft07.com/send/{sendkey}.send"
    try:
        response = await client.post(url, json=build_serverchan_payload(result))
    except httpx.RequestError as exc:
        raise NetworkError(f"ServerChan3 notification failed: {exc}") from exc
    if response.status_code >= 400:
        raise NetworkError(f"ServerChan3 notification failed: HTTP {response.status_code} {response.text[:200]}")
