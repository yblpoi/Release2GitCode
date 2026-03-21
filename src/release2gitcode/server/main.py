"""Server module entrypoint."""

from __future__ import annotations

import uvicorn

from release2gitcode.core.config import settings


def main() -> None:
    uvicorn.run("release2gitcode.server.app:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
