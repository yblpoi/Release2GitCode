"""Application error types."""


class AppError(Exception):
    """Base application error with an HTTP-friendly shape."""

    code = "app_error"
    status_code = 500

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message or self.__class__.__name__


class CryptoGenerationError(AppError):
    code = "crypto_generation_error"
    status_code = 500

    def __init__(self, message: str = "Failed to generate RSA keys") -> None:
        super().__init__(message)


class MissingAPIKeyError(AppError):
    code = "missing_api_key"
    status_code = 401

    def __init__(self, message: str = "X-API-Key header is missing") -> None:
        super().__init__(message)


class InvalidAPIKeyError(AppError):
    code = "invalid_api_key"
    status_code = 401

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(message)


class InvalidAPIKeyFormatError(AppError):
    code = "invalid_api_key_format"
    status_code = 401

    def __init__(self, message: str = "Invalid API key format. Must be 64 characters, start with 'r2gc-', and contain only letters, digits, and hyphens") -> None:
        super().__init__(message)


class TokenDecryptionError(AppError):
    code = "token_decryption_error"
    status_code = 400

    def __init__(self, message: str = "Failed to decrypt the provided secret") -> None:
        super().__init__(message)


class InvalidGitHubURLError(AppError):
    code = "invalid_github_url"
    status_code = 400

    def __init__(self, url: str, message: str = "Invalid GitHub Release URL") -> None:
        super().__init__(f"{message}: {url}")


class InvalidGitCodeURLError(AppError):
    code = "invalid_gitcode_url"
    status_code = 400

    def __init__(self, url: str, message: str = "Invalid GitCode repository URL") -> None:
        super().__init__(f"{message}: {url}")


class GitHubReleaseNotFound(AppError):
    code = "github_release_not_found"
    status_code = 404

    def __init__(self, owner: str, repo: str, tag: str) -> None:
        super().__init__(f"GitHub Release not found: {owner}/{repo} tag {tag}")


class GitCodeAuthError(AppError):
    code = "gitcode_auth_error"
    status_code = 400

    def __init__(self, message: str = "GitCode authentication failed") -> None:
        super().__init__(message)


class NetworkError(AppError):
    code = "network_error"
    status_code = 503

    def __init__(self, message: str = "Network request failed") -> None:
        super().__init__(message)


class HTTPSRequiredError(AppError):
    code = "https_required"
    status_code = 426

    def __init__(self, message: str = "HTTPS is required for all API requests") -> None:
        super().__init__(message)


class ConfigurationError(AppError):
    code = "configuration_error"
    status_code = 400

    def __init__(self, message: str = "Invalid configuration") -> None:
        super().__init__(message)
