"""应用配置"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置"""

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # HTTPS 要求
    require_https: bool = True

    # API 密钥哈希（bcrypt 哈希后的值，不存储明文）
    api_key_hash: str = ""

    # 限流配置
    rate_limit_public_key: str = "10/minute"
    rate_limit_sync: str = "5/minute"

    # GitHub API 配置
    github_api_base: str = "https://api.github.com"

    # GitCode API 配置
    gitcode_api_base: str = "https://api.gitcode.com/api/v5"

    # 下载配置
    chunk_size: int = 1024 * 1024  # 1MB
    max_file_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    upload_attempts: int = 5

    # 默认重试配置
    retry_delay_seconds: float = 1.0

    model_config = ConfigDict(
        env_prefix="",
        case_sensitive=False,
    )


settings = Settings()
