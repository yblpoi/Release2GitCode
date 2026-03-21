"""Settings and environment helpers."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from release2gitcode.core.errors import ConfigurationError


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    require_https: bool = True
    api_key_hash: str = ""
    api_key_length: int = 64
    github_api_base: str = "https://api.github.com"
    gitcode_api_base: str = "https://api.gitcode.com/api/v5"
    chunk_size: int = 1024 * 1024
    max_file_size: int = 10 * 1024 * 1024 * 1024
    upload_attempts: int = 5
    http_timeout_seconds: float = 30.0
    http_max_connections: int = 100
    http_max_keepalive_connections: int = 20
    retry_delay_seconds: float = 1.0
    model_config = ConfigDict(env_prefix="", case_sensitive=False)


settings = Settings()


def parse_multiline_files_env(value: str) -> list[Path]:
    return [Path(line.strip()) for line in value.splitlines() if line.strip()]


def discover_default_assets(asset_dir: Path) -> list[Path]:
    if not asset_dir.exists():
        raise ConfigurationError(f"Default asset directory does not exist: {asset_dir}")
    if not asset_dir.is_dir():
        raise ConfigurationError(f"Default asset path is not a directory: {asset_dir}")
    files = sorted(path for path in asset_dir.iterdir() if path.is_file())
    if not files:
        raise ConfigurationError(f"No files found in default asset directory: {asset_dir}")
    return files


def getenv_str(name: str) -> str:
    return os.getenv(name, "").strip()
