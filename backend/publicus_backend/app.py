from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from publicus_backend.routers import business_benefits, grants, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="Publicus API",
        version="0.0.1",
        description="FastAPI wrapper around Open Canada grants and business support datasets.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(grants.router)
    app.include_router(business_benefits.router)
    app.include_router(business_benefits.legacy_router)
    return app


app = create_app()
