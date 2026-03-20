"""Pydantic 数据模型"""

from pydantic import BaseModel, field_validator
from pydantic.networks import HttpUrl
from typing import Optional


class GetPublicKeyResponse(BaseModel):
    """获取公钥响应"""

    public_key: str
    key_id: str


class SyncRequest(BaseModel):
    """同步请求"""

    github_release_url: HttpUrl
    gitcode_repo_url: HttpUrl
    encrypted_gitcode_token: str

    @field_validator("github_release_url")
    @classmethod
    def github_url_must_be_github(cls, v: HttpUrl) -> HttpUrl:
        if v.host != "github.com":
            raise ValueError("github_release_url must be a GitHub URL (host github.com)")
        return v

    @field_validator("gitcode_repo_url")
    @classmethod
    def gitcode_url_must_be_gitcode(cls, v: HttpUrl) -> HttpUrl:
        if v.host != "gitcode.com":
            raise ValueError("gitcode_repo_url must be a GitCode URL (host gitcode.com)")
        return v


class SyncResponse(BaseModel):
    """同步响应"""

    task_id: str
    status: str
    message: str
    processed_assets: int
    skipped_assets: int
    failed_assets: list[str]


class ErrorDetail(BaseModel):
    """错误详情"""

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """统一错误响应"""

    error: ErrorDetail


class GitHubAsset(BaseModel):
    """GitHub Release Asset 信息"""

    id: int
    name: str
    size: int
    browser_download_url: str


class GitHubReleaseInfo(BaseModel):
    """GitHub Release 信息"""

    tag_name: str
    name: Optional[str] = None
    body: Optional[str] = None
    assets: list[GitHubAsset]
