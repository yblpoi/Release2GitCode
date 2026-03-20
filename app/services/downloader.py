"""流式下载器 - 针对小硬盘优化，逐个文件分块下载，不保存到磁盘

直接将下载的分块传递给上传器，不占用磁盘空间
"""

from typing import AsyncIterator, Callable
import httpx

from app.config.settings import settings
from app.models.schemas import GitHubAsset
from app.exceptions.errors import NetworkError


class StreamDownloader:
    """流式下载器

    从 GitHub 下载 asset，以分块形式流式返回数据，
    不写入本地磁盘，直接传递给上传器。
    """

    def __init__(self, asset: GitHubAsset, chunk_size: int = settings.chunk_size) -> None:
        self.asset = asset
        self.chunk_size = chunk_size
        self._total_bytes = asset.size

    async def download_stream(self, progress_callback: Callable[[int], None]) -> AsyncIterator[bytes]:
        """异步流式下载

        Args:
            progress_callback: 进度回调，参数为当前已下载字节数

        Yields:
            数据块 bytes

        Raises:
            NetworkError: 下载失败
        """

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "GET",
                    self.asset.browser_download_url,
                    follow_redirects=True
                ) as response:
                    if response.status_code >= 400:
                        raise NetworkError(
                            f"Download failed for {self.asset.name}: HTTP {response.status_code}"
                        )

                    downloaded_bytes = 0
                    async for chunk in response.aiter_bytes(chunk_size=self.chunk_size):
                        downloaded_bytes += len(chunk)
                        progress_callback(downloaded_bytes)
                        yield chunk
            except httpx.RequestError as e:
                raise NetworkError(f"Download failed for {self.asset.name}: {str(e)}") from e

    @property
    def total_bytes(self) -> int:
        """获取文件总大小"""

        return self._total_bytes
