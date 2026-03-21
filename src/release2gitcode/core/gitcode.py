"""GitCode release and upload helpers."""

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable
from urllib import parse

import httpx

from release2gitcode.core.config import settings
from release2gitcode.core.errors import GitCodeAuthError, InvalidGitCodeURLError, NetworkError
from release2gitcode.core.models import GitCodeRepoRef, GitHubAsset


def parse_gitcode_repo_url(url: str) -> GitCodeRepoRef:
    parsed = parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "gitcode.com":
        raise InvalidGitCodeURLError(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise InvalidGitCodeURLError(url)
    owner = parts[0]
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return GitCodeRepoRef(repo_url=f"https://gitcode.com/{owner}/{repo}", owner=owner, repo=repo)


class GitCodeReleaseClient:
    def __init__(self, client: httpx.AsyncClient, token: str, owner: str, repo: str, api_base: str | None = None) -> None:
        self.client = client
        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_base = api_base or settings.gitcode_api_base

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "Release2GitCode/3.0",
        }

    def _release_url(self, suffix: str = "") -> str:
        owner = parse.quote(self.owner, safe="")
        repo = parse.quote(self.repo, safe="")
        return f"{self.api_base}/repos/{owner}/{repo}/releases{suffix}"

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        try:
            response = await self.client.request(method, url, headers=self._headers(), json=json, params=params)
        except httpx.RequestError as exc:
            raise NetworkError(f"GitCode request failed: {exc}") from exc
        if response.status_code in {401, 403}:
            raise GitCodeAuthError()
        if response.status_code >= 400:
            raise NetworkError(f"GitCode request failed: HTTP {response.status_code} {response.text[:200]}")
        try:
            return response.json()
        except ValueError:
            return response.text

    async def get_release_by_tag(self, tag: str) -> dict[str, Any] | None:
        url = self._release_url(f"/tags/{parse.quote(tag, safe='')}")
        try:
            response = await self.client.get(url, headers=self._headers())
        except httpx.RequestError as exc:
            raise NetworkError(f"Failed to check release: {exc}") from exc
        if response.status_code == 404:
            return None
        if response.status_code == 400 and "404 Release Not Found" in response.text:
            return None
        if response.status_code in {401, 403}:
            raise GitCodeAuthError()
        if response.status_code >= 400:
            raise NetworkError(f"Failed to check release: HTTP {response.status_code}")
        return response.json()

    async def ensure_release(self, tag: str, name: str | None, body: str | None, target_branch: str | None = None) -> dict[str, Any]:
        existing = await self.get_release_by_tag(tag)
        payload = {"tag_name": tag, "name": name or tag, "body": body or ""}
        if target_branch:
            payload["target_commitish"] = target_branch
        if existing is None:
            return await self._request_json("POST", self._release_url(), json=payload)
        needs_update = existing.get("name") != payload["name"] or existing.get("body") != payload["body"] or existing.get("tag_name") != tag
        if not needs_update:
            return existing
        candidates = [tag]
        if existing.get("id") not in (None, ""):
            candidates.append(str(existing["id"]))
        last_error: Exception | None = None
        for candidate in candidates:
            try:
                return await self._request_json("PATCH", self._release_url(f"/{parse.quote(candidate, safe='')}"), json=payload)
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        return existing

    def get_existing_asset_names(self, release: dict[str, Any]) -> set[str]:
        names: set[str] = set()
        for asset in release.get("assets", []):
            if not isinstance(asset, dict):
                continue
            if str(asset.get("type") or "").lower() != "attach":
                continue
            name = str(asset.get("name") or "").strip()
            if name:
                names.add(name)
        return names

    async def get_upload_target(self, tag: str, asset_name: str) -> dict[str, Any] | str:
        return await self._request_json(
            "GET",
            self._release_url(f"/{parse.quote(tag, safe='')}/upload_url"),
            params={"file_name": asset_name},
        )

    @staticmethod
    def _extract_upload_target(
        upload_response: dict[str, Any] | str,
    ) -> tuple[str, str, dict[str, str], dict[str, str] | None, str | None, str]:
        if isinstance(upload_response, str):
            return upload_response, "PUT", {}, None, "file_name", "file"
        upload_url = str(upload_response.get("upload_url") or upload_response.get("url") or "")
        if not upload_url:
            raise NetworkError("Upload URL missing in response")
        headers = upload_response.get("headers") if isinstance(upload_response.get("headers"), dict) else {}
        form_fields = None
        for key in ("form_fields", "fields", "form", "data"):
            if isinstance(upload_response.get(key), dict):
                form_fields = {str(k): str(v) for k, v in upload_response[key].items()}
                break
        filename_query_key = upload_response.get("filename_query_key")
        if filename_query_key is None and upload_response.get("append_filename") is not False:
            filename_query_key = "file_name"
        if filename_query_key is not None:
            filename_query_key = str(filename_query_key)
        file_field_name = upload_response.get("file_field_name") or upload_response.get("file_field") or "file"
        return upload_url, str(upload_response.get("method") or "PUT").upper(), dict(headers), form_fields, filename_query_key, str(file_field_name)

    @staticmethod
    def _append_filename_query(url: str, filename: str, query_key: str | None) -> str:
        if not query_key:
            return url
        parsed = parse.urlsplit(url)
        query = parse.parse_qsl(parsed.query, keep_blank_values=True)
        if query_key not in {key for key, _ in query}:
            query.append((query_key, filename))
        return parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parse.urlencode(query), parsed.fragment))

    async def upload_bytes(self, tag: str, path: Path, upload_attempts: int, timeout_seconds: float | None) -> Any:
        async def stream_factory() -> AsyncIterator[bytes]:
            with path.open("rb") as handle:
                while True:
                    chunk = handle.read(settings.chunk_size)
                    if not chunk:
                        break
                    yield chunk

        asset = GitHubAsset(id=0, name=path.name, size=path.stat().st_size, browser_download_url="")
        return await self.upload_stream(tag, asset, stream_factory, upload_attempts=upload_attempts, timeout_seconds=timeout_seconds)

    async def upload_stream(
        self,
        tag: str,
        asset: GitHubAsset,
        stream_factory: Callable[[], AsyncIterator[bytes]],
        *,
        upload_attempts: int,
        timeout_seconds: float | None,
    ) -> Any:
        upload_response = await self.get_upload_target(tag, asset.name)
        upload_url, method, headers, form_fields, filename_query_key, file_field_name = self._extract_upload_target(upload_response)
        upload_url = self._append_filename_query(upload_url, asset.name, filename_query_key)
        content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        request_headers = {"User-Agent": "Release2GitCode/3.0", **headers}

        for attempt in range(1, upload_attempts + 1):
            try:
                if form_fields:
                    boundary = f"----Release2GitCode{asset.id or 'upload'}"
                    request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
                    content = self._multipart_stream(boundary, form_fields, asset.name, content_type, stream_factory, file_field_name)
                else:
                    request_headers.setdefault("Content-Type", content_type)
                    content = stream_factory()
                response = await self.client.request(method, upload_url, headers=request_headers, content=content, timeout=timeout_seconds)
            except httpx.RequestError as exc:
                if attempt == upload_attempts:
                    raise NetworkError(
                        f"Upload failed for {asset.name}: method={method} file_field_name={file_field_name} error={exc}"
                    ) from exc
                await asyncio.sleep(settings.retry_delay_seconds)
                continue

            if response.status_code in {401, 403}:
                raise GitCodeAuthError()
            if response.status_code >= 500 and attempt < upload_attempts:
                await asyncio.sleep(settings.retry_delay_seconds)
                continue
            if response.status_code >= 400:
                raise NetworkError(
                    f"Upload failed for {asset.name}: method={method} file_field_name={file_field_name} "
                    f"HTTP {response.status_code} {response.text[:200]}"
                )
            try:
                return response.json() if response.content else None
            except ValueError:
                return response.text
        raise NetworkError(f"Upload failed for {asset.name}")

    @staticmethod
    async def _multipart_stream(
        boundary: str,
        form_fields: dict[str, str],
        filename: str,
        content_type: str,
        stream_factory: Callable[[], AsyncIterator[bytes]],
        file_field_name: str,
    ) -> AsyncIterator[bytes]:
        for key, value in form_fields.items():
            yield (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        yield (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        async for chunk in stream_factory():
            yield chunk
        yield f"\r\n--{boundary}--\r\n".encode("utf-8")
