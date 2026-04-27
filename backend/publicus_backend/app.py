from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from publicus_backend.core.env import load_root_env

load_root_env()

from publicus_backend.routers import business_benefits, grants, health, opportunities, pipeline, profile_copilot, search

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Publicus API",
        version="0.0.1",
        description="FastAPI wrapper around Open Canada grants and business support datasets.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(grants.router)
    app.include_router(business_benefits.router)
    app.include_router(business_benefits.legacy_router)
    app.include_router(search.router)
    app.include_router(profile_copilot.router)
    app.include_router(opportunities.router)
    app.include_router(pipeline.router)
    return app


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("PUBLICUS_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


app = create_app()
