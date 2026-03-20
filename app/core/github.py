"""GitHub URL 解析和 Release 信息获取"""

from urllib.parse import urlparse
from typing import Tuple, Optional

import httpx

from app.config.settings import settings
from app.models.schemas import GitHubReleaseInfo, GitHubAsset
from app.exceptions.errors import InvalidGitHubURLError, GitHubReleaseNotFound, NetworkError


def parse_github_release_url(url: str) -> Tuple[str, str, str]:
    """解析 GitHub Release URL，提取 owner、repo、tag

    支持格式：
    - https://github.com/owner/repo/releases/tag/v1.0.0
    - https://github.com/owner/repo/releases/download/v1.0.0/file.zip

    Returns:
        (owner, repo, tag)

    Raises:
        InvalidGitHubURLError: URL 格式无效
    """

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidGitHubURLError(url)

    if parsed.netloc != "github.com":
        raise InvalidGitHubURLError(url)

    parts = [p for p in parsed.path.split("/") if p]

    if len(parts) >= 5 and parts[2] == "releases" and parts[3] == "tag":
        owner, repo = parts[0], parts[1]
        tag = "/".join(parts[4:])
        return owner, repo, tag

    if len(parts) >= 6 and parts[2] == "releases" and parts[3] == "download":
        owner, repo = parts[0], parts[1]
        tag = parts[4]
        return owner, repo, tag

    raise InvalidGitHubURLError(url, "Could not extract owner, repo, and tag from URL")


async def get_release_info(owner: str, repo: str, tag: str) -> GitHubReleaseInfo:
    """获取 GitHub Release 信息

    Args:
        owner: 仓库所有者
        repo: 仓库名
        tag: 标签名

    Returns:
        GitHubReleaseInfo 包含 assets 列表

    Raises:
        GitHubReleaseNotFound: Release 不存在
        NetworkError: 网络请求失败
    """

    url = f"{settings.github_api_base}/repos/{owner}/{repo}/releases/tags/{tag}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, follow_redirects=True)
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to connect to GitHub API: {str(e)}") from e

    if response.status_code == 404:
        raise GitHubReleaseNotFound(owner, repo, tag)

    if response.status_code >= 400:
        raise NetworkError(f"GitHub API returned HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise NetworkError(f"Failed to parse GitHub API response: {str(e)}") from e

    assets: list[GitHubAsset] = []
    for asset in data.get("assets", []):
        if (
            isinstance(asset, dict)
            and "id" in asset
            and "name" in asset
            and "size" in asset
            and "browser_download_url" in asset
        ):
            assets.append(
                GitHubAsset(
                    id=asset["id"],
                    name=asset["name"],
                    size=asset["size"],
                    browser_download_url=asset["browser_download_url"],
                )
            )

    return GitHubReleaseInfo(
        tag_name=data.get("tag_name", tag),
        name=data.get("name"),
        body=data.get("body"),
        assets=assets,
    )
