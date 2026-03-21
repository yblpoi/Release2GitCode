"""Shared data models."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import HttpUrl


class GetPublicKeyResponse(BaseModel):
    public_key: str
    key_id: str


class SyncRequest(BaseModel):
    github_release_url: HttpUrl
    gitcode_repo_url: HttpUrl
    encrypted_gitcode_token: str
    encrypted_github_token: str | None = None
    encrypted_serverchan3_sendkey: str | None = None

    @field_validator("github_release_url")
    @classmethod
    def github_url_must_be_github(cls, value: HttpUrl) -> HttpUrl:
        if value.host != "github.com":
            raise ValueError("github_release_url must use host github.com")
        return value

    @field_validator("gitcode_repo_url")
    @classmethod
    def gitcode_url_must_be_gitcode(cls, value: HttpUrl) -> HttpUrl:
        if value.host != "gitcode.com":
            raise ValueError("gitcode_repo_url must use host gitcode.com")
        return value


class SyncResponse(BaseModel):
    task_id: str
    status: str
    message: str
    processed_assets: int
    skipped_assets: int
    failed_assets: list[str]


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class GitHubAsset(BaseModel):
    id: int
    name: str
    size: int
    browser_download_url: str


class GitHubReleaseInfo(BaseModel):
    tag_name: str
    name: Optional[str] = None
    body: Optional[str] = None
    assets: list[GitHubAsset] = Field(default_factory=list)


class GitCodeRepoRef(BaseModel):
    repo_url: str
    owner: str
    repo: str


class LocalUploadConfig(BaseModel):
    token: str
    repo_url: str
    tag: str
    release_name: str | None = None
    release_body: str | None = None
    target_branch: str | None = None
    upload_attempts: int = 5
    timeout_seconds: float | None = None
    files: list[Path]


class SyncResult(BaseModel):
    task_id: str
    github_release_url: str
    gitcode_repo_url: str
    processed_assets: int
    skipped_assets: int
    failed_assets: list[str]
    total_assets: int
    duration_seconds: float
    notification_warning: str | None = None

    @property
    def is_success(self) -> bool:
        return not self.failed_assets
