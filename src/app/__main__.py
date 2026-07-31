"""Run the API using the values in ``.env``: ``python -m app``.

``make dev`` is the friendlier way in during development. This entrypoint
exists so ``API_HOST`` / ``API_PORT`` / ``API_WORKERS`` are honoured in
production without repeating them on a command line.
"""

from __future__ import annotations

import uvicorn

from app.core.config import settings


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        # Reload and multiple workers are mutually exclusive in uvicorn.
        workers=None if settings.api_reload else settings.api_workers,
        access_log=False,  # RequestContextMiddleware already logs every request.
        proxy_headers=True,
        forwarded_allow_ips="*" if settings.is_production else None,
    )


if __name__ == "__main__":
    main()
