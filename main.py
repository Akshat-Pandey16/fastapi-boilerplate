from typing import Any, Dict

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import api_config, app_config, cors_config
from core.router import router as api_router

app = FastAPI(
    title=api_config.TITLE,
    description=api_config.DESCRIPTION,
    version=api_config.VERSION,
    docs_url="/docs" if app_config.is_development else None,
    redoc_url="/redoc" if app_config.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.ALLOW_ORIGINS,
    allow_credentials=cors_config.ALLOW_CREDENTIALS,
    allow_methods=cors_config.ALLOW_METHODS,
    allow_headers=cors_config.ALLOW_HEADERS,
)

app.include_router(api_router)


@app.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    return {
        "message": f"Welcome to {api_config.TITLE}",
        "version": api_config.VERSION,
        "environment": app_config.ENVIRONMENT,
        "docs": (
            "/docs"
            if app_config.is_development
            else "Documentation disabled in production"
        ),
        "redoc": "/redoc" if app_config.is_development else None,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=api_config.HOST,
        port=api_config.PORT,
        reload=api_config.RELOAD,
        reload_dirs=["api", "core"],
    )
