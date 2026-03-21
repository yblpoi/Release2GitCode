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
    title = "同步成功" if result.is_success else "同步失败"
    desp = "\n".join(
        [
            f"触发时间：{result.triggered_at}",
            f"GitHub发行版链接：{result.github_release_url}",
            f"GitCode仓库：{result.gitcode_repo_url}",
        ]
    )
    return {
        "title": title,
        "desp": desp,
        "short": title,
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
