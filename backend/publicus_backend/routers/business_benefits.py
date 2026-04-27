from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Path as PathParam, Query

from publicus_backend.core.errors import api_error
from publicus_backend.core.query import normalize_sort_order
from publicus_backend.services.business_benefits import (
    DEFAULT_LANGUAGE,
    DEFAULT_RENDER_WAIT_MS,
    DEFAULT_TOKEN,
    InnovationCanadaError,
    build_client,
    dataset_update_feed,
    first_programs,
    records_by_category,
)


router = APIRouter(prefix="/api/business-benefits", tags=["business-benefits"])
legacy_router = APIRouter(prefix="/api/innovation", tags=["innovation"])


@router.get("/first/{count}")
@legacy_router.get("/first/{count}")
def first_business_benefits_records(
    count: int = PathParam(
        ge=1,
        le=5000,
        description="Number of Business Benefits Finder records to return from the latest Open Canada XLSX resource.",
    ),
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        with build_client(timeout) as client:
            return first_programs(client, count)
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/update-feed")
@legacy_router.get("/update-feed")
def business_benefits_update_feed(
    timeout: float = Query(default=30.0, ge=5.0, le=120.0),
) -> dict[str, Any]:
    try:
        with build_client(timeout) as client:
            return dataset_update_feed(client)
    except Exception as exc:
        raise api_error(exc) from exc


def business_benefits_by_category_response(
    *,
    category: str | None,
    limit: int,
    offset: int,
    order: str,
    token: str,
    language: str,
    timeout: float,
    render_wait_ms: int,
) -> dict[str, Any]:
    try:
        sort_order = normalize_sort_order(order)
        return records_by_category(
            category=category,
            limit=limit,
            offset=offset,
            order=sort_order,
            token=token,
            language=language,
            timeout=timeout,
            render_wait_ms=render_wait_ms,
        )
    except HTTPException:
        raise
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except InnovationCanadaError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Could not fetch Business Benefits Finder records.",
                "error": str(exc),
            },
        ) from exc


@router.get("/by-category")
@legacy_router.get("/by-category")
def list_business_benefits_by_category(
    category: str | None = Query(
        default=None,
        description="Optional exact category name. Omit it to return all visible records sorted by category.",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", description="'asc' or 'desc'. Sorts by category, then title, then id."),
    token: str = Query(default=DEFAULT_TOKEN, description="Innovation Canada list token."),
    language: str = Query(default=DEFAULT_LANGUAGE, description="Innovation Canada language code."),
    timeout: float = Query(default=45.0, ge=10.0, le=180.0),
    render_wait_ms: int = Query(
        default=DEFAULT_RENDER_WAIT_MS,
        ge=5000,
        le=60000,
        description="Headless Chromium virtual-time budget used to let Salesforce render records.",
    ),
) -> dict[str, Any]:
    return business_benefits_by_category_response(
        category=category,
        limit=limit,
        offset=offset,
        order=order,
        token=token,
        language=language,
        timeout=timeout,
        render_wait_ms=render_wait_ms,
    )


@router.get("/by-category/{category}")
@legacy_router.get("/by-category/{category}")
def list_business_benefits_for_category(
    category: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", description="'asc' or 'desc'. Sorts by category, then title, then id."),
    token: str = Query(default=DEFAULT_TOKEN, description="Innovation Canada list token."),
    language: str = Query(default=DEFAULT_LANGUAGE, description="Innovation Canada language code."),
    timeout: float = Query(default=45.0, ge=10.0, le=180.0),
    render_wait_ms: int = Query(
        default=DEFAULT_RENDER_WAIT_MS,
        ge=5000,
        le=60000,
        description="Headless Chromium virtual-time budget used to let Salesforce render records.",
    ),
) -> dict[str, Any]:
    return business_benefits_by_category_response(
        category=category,
        limit=limit,
        offset=offset,
        order=order,
        token=token,
        language=language,
        timeout=timeout,
        render_wait_ms=render_wait_ms,
    )
