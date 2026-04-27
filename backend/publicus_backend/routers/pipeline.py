from __future__ import annotations

import os
import secrets
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Path, Query, Request

from publicus_backend.services.pipeline import (
    DEFAULT_INGEST_RECORDS,
    MAX_INGEST_RECORDS,
    MAX_LIMIT,
    PipelineConfigError,
    PipelineSourceError,
    ingest_source,
    pipeline_status,
    query_records,
)


router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/status")
def get_pipeline_status(timeout: float = Query(default=30.0, ge=5.0, le=120.0)) -> dict[str, Any]:
    try:
        return pipeline_status(timeout=timeout)
    except Exception as exc:
        raise pipeline_error(exc) from exc


@router.post("/ingest/{source}")
def ingest_pipeline_source(
    request: Request,
    source: str = Path(description="'grants' or 'business-benefits'."),
    max_records: int = Query(default=DEFAULT_INGEST_RECORDS, ge=1, le=MAX_INGEST_RECORDS),
    page_size: int = Query(default=1000, ge=1, le=5000),
    timeout: float = Query(default=60.0, ge=10.0, le=300.0),
    token: str | None = Query(default=None, description="Optional admin token. Prefer the x-publicus-admin-token header."),
) -> dict[str, Any]:
    require_pipeline_admin_token(request, token)

    try:
        return ingest_source(source, max_records=max_records, page_size=page_size, timeout=timeout)
    except Exception as exc:
        raise pipeline_error(exc) from exc


@router.get("/records")
def list_pipeline_records(
    source: str | None = Query(default=None, description="'grants' or 'business-benefits'."),
    limit: int = Query(default=100, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=False),
    active: bool | None = Query(default=None, description="Alias for active_only."),
    q: str | None = Query(default=None, max_length=250),
    timeout: float = Query(default=30.0, ge=5.0, le=120.0),
) -> dict[str, Any]:
    effective_active_only = active if active is not None else active_only

    try:
        result = query_records(
            source_value=source,
            limit=limit,
            offset=offset,
            active_only=effective_active_only,
            q=q,
            timeout=timeout,
        )
    except Exception as exc:
        raise pipeline_error(exc) from exc

    raw_records = [source_row_to_record(row) for row in result["records"]]
    return {
        "requested": limit,
        "count": len(raw_records),
        "total": result.get("count"),
        "source": result.get("source"),
        "active_only": effective_active_only,
        "offset": offset,
        "records": raw_records,
        "pipeline": {
            "available": True,
            "storage": "supabase",
        },
    }


def source_row_to_record(row: dict[str, Any]) -> dict[str, Any]:
    raw_record = row.get("raw_record")
    record = dict(raw_record) if isinstance(raw_record, dict) else {}

    fallback_fields = {
        "title": row.get("title"),
        "sponsor": row.get("sponsor"),
        "description": row.get("description"),
        "province": row.get("province"),
        "city": row.get("city"),
        "amount": row.get("amount"),
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
        "deadline_date": row.get("deadline_date"),
        "status": row.get("status"),
    }
    for key, value in fallback_fields.items():
        if value is not None and record.get(key) in (None, ""):
            record[key] = value

    record["_pipeline_id"] = row.get("id")
    record["_pipeline_source"] = row.get("source")
    record["_pipeline_source_id"] = row.get("source_id")
    record["_pipeline_fetched_at"] = row.get("fetched_at")
    return record


def require_pipeline_admin_token(request: Request, query_token: str | None) -> None:
    expected_token = os.getenv("PUBLICUS_PIPELINE_ADMIN_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(status_code=503, detail="Set PUBLICUS_PIPELINE_ADMIN_TOKEN to enable ingestion.")

    provided_token = (request.headers.get("x-publicus-admin-token") or query_token or "").strip()
    if not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid pipeline admin token.")


def pipeline_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PipelineConfigError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (PipelineSourceError, ValueError)):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            return HTTPException(status_code=503, detail="Pipeline storage rejected the configured Supabase key.")
        if status_code == 404:
            return HTTPException(status_code=503, detail="Pipeline storage tables are not migrated yet.")
        return HTTPException(status_code=502, detail="Pipeline storage returned an upstream error.")
    if isinstance(exc, httpx.HTTPError):
        return HTTPException(status_code=502, detail="Pipeline storage is temporarily unavailable.")
    return HTTPException(status_code=500, detail="Pipeline request failed.")
