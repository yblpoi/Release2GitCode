"""GitCode 流式上传器

接收从 GitHub 下载的流式数据，直接上传到 GitCode Release
不写入本地磁盘，针对小硬盘环境优化
"""

import mimetypes
from urllib import parse
from typing import AsyncIterator, Tuple, Optional, Dict, Any, Callable

import httpx

from app.config.settings import settings
from app.models.schemas import GitHubAsset
from app.exceptions.errors import GitCodeAuthError, NetworkError
from app.services.downloader import StreamDownloader


def parse_gitcode_repo_url(url: str) -> Tuple[str, str]:
    """解析 GitCode 仓库 URL，提取 owner 和 repo"""

    parsed = parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    if len(parts) >= 2:
        owner = parts[0]
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo

    raise ValueError(f"Invalid GitCode repository URL: {url}")


class GitCodeStreamUploader:
    """GitCode 流式上传器

    直接流式上传从 GitHub 下载的数据，不占用磁盘空间
    """

    def __init__(self, token: str, owner: str, repo: str, tag: str) -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.tag = tag
        self._api_base = settings.gitcode_api_base

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "Release2GitCode/2.0",
        }

    async def ensure_release(self, name: Optional[str], body: Optional[str]) -> Dict[str, Any]:
        """确保 release 存在，返回 release 信息"""

        url = f"{self._api_base}/repos/{parse.quote(self.owner, safe='')}/{parse.quote(self.repo, safe='')}/releases/tags/{parse.quote(self.tag, safe='')}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self._build_headers())
            except httpx.RequestError as e:
                raise NetworkError(f"Failed to check release: {str(e)}") from e

        if response.status_code == 404:
            return await self._create_release(name, body)

        if response.status_code >= 400:
            if response.status_code == 401 or response.status_code == 403:
                raise GitCodeAuthError()
            raise NetworkError(f"Failed to check release: HTTP {response.status_code}")

        return response.json()

    async def _create_release(self, name: Optional[str], body: Optional[str]) -> Dict[str, Any]:
        """创建 release"""

        url = f"{self._api_base}/repos/{parse.quote(self.owner, safe='')}/{parse.quote(self.repo, safe='')}/releases"

        payload = {
            "tag_name": self.tag,
            "name": name or self.tag,
            "body": body or "",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._build_headers(),
                    json=payload,
                )
            except httpx.RequestError as e:
                raise NetworkError(f"Failed to create release: {str(e)}") from e

        if response.status_code >= 400:
            if response.status_code == 401 or response.status_code == 403:
                raise GitCodeAuthError()
            raise NetworkError(f"Failed to create release: HTTP {response.status_code}")

        return response.json()

    def get_existing_asset_names(self, release: Dict[str, Any]) -> set[str]:
        """获取已存在的附件名称集合"""

        names: set[str] = set()
        assets = release.get("assets", [])

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            if str(asset.get("type") or "").lower() != "attach":
                continue
            name = str(asset.get("name") or "").strip()
            if name:
                names.add(name)

        return names

    async def get_upload_target(self, asset_name: str) -> Dict[str, Any]:
        """获取上传地址"""

        url = f"{self._api_base}/repos/{parse.quote(self.owner, safe='')}/{parse.quote(self.repo, safe='')}/releases/{parse.quote(self.tag, safe='')}/upload_url"

        params = {"file_name": asset_name}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers=self._build_headers(),
                    params=params,
                )
            except httpx.RequestError as e:
                raise NetworkError(f"Failed to get upload URL: {str(e)}") from e

        if response.status_code >= 400:
            if response.status_code == 401 or response.status_code == 403:
                raise GitCodeAuthError()
            raise NetworkError(f"Failed to get upload URL: HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError:
            return {"url": response.text.strip()}

    def _extract_upload_info(self, upload_response: Dict[str, Any]) -> Tuple[str, str, Optional[Dict[str, str]], Optional[Dict[str, str]]]:
        """提取上传信息

        Returns:
            (upload_url, method, headers, form_fields)
        """

        if isinstance(upload_response, str):
            return upload_response, "PUT", None, None

        if not isinstance(upload_response, dict):
            return str(upload_response), "PUT", None, None

        upload_url = upload_response.get("upload_url") or upload_response.get("url")
        if not upload_url:
            raise NetworkError("Upload URL missing in response")

        method = str(upload_response.get("method") or "PUT").upper()

        headers = None
        if "headers" in upload_response and isinstance(upload_response["headers"], dict):
            headers = {str(k): str(v) for k, v in upload_response["headers"].items()}

        form_fields = None
        for key in ("form_fields", "fields", "form", "data"):
            if key in upload_response and isinstance(upload_response[key], dict):
                form_fields = {str(k): str(v) for k, v in upload_response[key].items()}
                break

        return str(upload_url), method, headers, form_fields

    async def upload_stream(
        self,
        asset: GitHubAsset,
        downloader: StreamDownloader,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """流式上传一个文件

        直接从 downloader 读取分块，发送到 GitCode，不写入磁盘

        Args:
            asset: GitHub asset 信息
            downloader: 流式下载器
            progress_callback: 进度回调

        Returns:
            True 上传成功，False 失败
        """

        upload_response = await self.get_upload_target(asset.name)
        upload_url, method, headers, form_fields = self._extract_upload_info(upload_response)

        filename_query_key = "file_name"
        if "filename_query_key" in upload_response:
            filename_query_key = upload_response["filename_query_key"]
        elif upload_response.get("append_filename") is False:
            filename_query_key = None

        if filename_query_key:
            parsed = parse.urlsplit(upload_url)
            query = parse.parse_qsl(parsed.query, keep_blank_values=True)
            existing_keys = {key for key, _ in query}
            if filename_query_key not in existing_keys:
                query.append((filename_query_key, asset.name))
            upload_url = parse.urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, parse.urlencode(query), parsed.fragment)
            )

        content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"

        uploaded_bytes = 0
        total_bytes = downloader.total_bytes

        async def iter_chunks() -> AsyncIterator[bytes]:
            nonlocal uploaded_bytes
            async for chunk in downloader.download_stream(lambda dl_bytes: None):
                uploaded_bytes += len(chunk)
                if progress_callback:
                    progress_callback(uploaded_bytes)
                yield chunk

        request_headers: Dict[str, str] = {
            "User-Agent": "Release2GitCode/2.0",
        }
        if headers:
            request_headers.update(headers)

        if not form_fields:
            request_headers.setdefault("Content-Type", content_type)
            content_iterator = iter_chunks()
        else:
            boundary = f"----Release2GitCodeStream{asset.id}"
            content_iterator = self._build_multipart_stream(
                form_fields, asset.name, content_type, iter_chunks, boundary
            )
            request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        for attempt in range(1, settings.upload_attempts + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method,
                        upload_url,
                        headers=request_headers,
                        content=content_iterator,
                        timeout=None,
                    )

                if response.status_code >= 500:
                    if attempt < settings.upload_attempts:
                        continue
                    raise NetworkError(f"Upload failed after {attempt} attempts: HTTP {response.status_code}")

                if response.status_code >= 400:
                    if response.status_code == 401 or response.status_code == 403:
                        raise GitCodeAuthError()
                    raise NetworkError(f"Upload failed: HTTP {response.status_code}")

                return True

            except httpx.RequestError:
                if attempt < settings.upload_attempts:
                    continue
                raise

        return False

    async def _build_multipart_stream(
        self,
        form_fields: Dict[str, str],
        filename: str,
        content_type: str,
        content_iterator: AsyncIterator[bytes],
        boundary: str,
    ) -> AsyncIterator[bytes]:
        """构建 multipart 流"""

        for key, value in form_fields.items():
            preamble = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
            yield preamble

        file_preamble = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        yield file_preamble

        async for chunk in content_iterator:
            yield chunk

        closing = f"\r\n--{boundary}--\r\n".encode("utf-8")
        yield closing
