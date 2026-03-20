"""自定义异常定义"""


class AppError(Exception):
    """应用自定义异常基类"""

    code: str
    status_code: int

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class CryptoGenerationError(AppError):
    """RSA 密钥生成失败"""

    code = "crypto_generation_error"
    status_code = 500

    def __init__(self, message: str = "Failed to generate RSA keys") -> None:
        super().__init__(message)


class MissingAPIKeyError(AppError):
    """缺少 API 密钥"""

    code = "missing_api_key"
    status_code = 401

    def __init__(self, message: str = "X-API-Key header is missing") -> None:
        super().__init__(message)


class InvalidAPIKeyError(AppError):
    """API 密钥无效"""

    code = "invalid_api_key"
    status_code = 401

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(message)


class TokenDecryptionError(AppError):
    """令牌解密失败"""

    code = "token_decryption_error"
    status_code = 400

    def __init__(self, message: str = "Failed to decrypt GitCode token. The token may be encrypted with an incorrect public key or corrupted.") -> None:
        super().__init__(message)


class InvalidGitHubURLError(AppError):
    """GitHub URL 解析失败"""

    code = "invalid_github_url"
    status_code = 400

    def __init__(self, url: str, message: str = "Invalid GitHub Release URL") -> None:
        super().__init__(f"{message}: {url}")
        self.url = url


class GitHubReleaseNotFound(AppError):
    """GitHub Release 不存在"""

    code = "github_release_not_found"
    status_code = 404

    def __init__(self, owner: str, repo: str, tag: str, message: str = "GitHub Release not found") -> None:
        super().__init__(f"{message}: {owner}/{repo} tag {tag}")
        self.owner = owner
        self.repo = repo
        self.tag = tag


class GitCodeAuthError(AppError):
    """GitCode 认证失败"""

    code = "gitcode_auth_error"
    status_code = 400

    def __init__(self, message: str = "GitCode authentication failed. The token may be invalid.") -> None:
        super().__init__(message)


class NetworkError(AppError):
    """网络请求失败"""

    code = "network_error"
    status_code = 503

    def __init__(self, message: str = "Network request failed") -> None:
        super().__init__(message)


class RateLimitExceeded(AppError):
    """请求超限"""

    code = "rate_limit_exceeded"
    status_code = 429

    def __init__(self, message: str = "Too many requests, please try again later") -> None:
        super().__init__(message)


class HTTPSRequiredError(AppError):
    """需要 HTTPS"""

    code = "https_required"
    status_code = 426

    def __init__(self, message: str = "HTTPS is required for all API requests") -> None:
        super().__init__(message)
