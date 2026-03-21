"""GitHub release metadata helpers."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from release2gitcode.core.errors import GitHubReleaseNotFound, InvalidGitHubURLError, NetworkError
from release2gitcode.core.models import GitHubAsset, GitHubReleaseInfo


def parse_github_release_url(url: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "github.com":
        raise InvalidGitHubURLError(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 5 and parts[2] == "releases" and parts[3] == "tag":
        return parts[0], parts[1], "/".join(parts[4:])
    if len(parts) >= 6 and parts[2] == "releases" and parts[3] == "download":
        return parts[0], parts[1], parts[4]
    raise InvalidGitHubURLError(url, "Could not extract owner, repo, and tag from URL")


async def get_release_info(
    client: httpx.AsyncClient,
    github_api_base: str,
    owner: str,
    repo: str,
    tag: str,
    github_token: str | None = None,
) -> GitHubReleaseInfo:
    url = f"{github_api_base}/repos/{owner}/{repo}/releases/tags/{tag}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Release2GitCode/3.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    try:
        response = await client.get(url, headers=headers)
    except httpx.RequestError as exc:
        raise NetworkError(f"Failed to connect to GitHub API: {exc}") from exc

    if response.status_code == 404:
        raise GitHubReleaseNotFound(owner, repo, tag)
    if response.status_code >= 400:
        raise NetworkError(f"GitHub API returned HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise NetworkError(f"Failed to parse GitHub API response: {exc}") from exc

    assets = [
        GitHubAsset(
            id=asset["id"],
            name=asset["name"],
            size=asset["size"],
            browser_download_url=asset["browser_download_url"],
        )
        for asset in data.get("assets", [])
        if isinstance(asset, dict)
        and {"id", "name", "size", "browser_download_url"}.issubset(asset.keys())
    ]
    return GitHubReleaseInfo(
        tag_name=data.get("tag_name", tag),
        name=data.get("name"),
        body=data.get("body"),
        assets=assets,
    )
