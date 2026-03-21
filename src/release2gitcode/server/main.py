"""Server module entrypoint."""

from __future__ import annotations

import uvicorn

from release2gitcode.core.config import settings


def main() -> None:
    uvicorn.run(
        "release2gitcode.server.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.server_log_level,
        access_log=settings.server_access_log,
    )


if __name__ == "__main__":
    main()
