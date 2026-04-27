from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, HTTPException, Path as PathParam, Query

from publicus_backend.core.errors import api_error
from publicus_backend.core.query import (
    SORT_ORDERS,
    calendar_year_range,
    normalize_calendar_date_field,
    normalize_query_string,
    normalize_sort_order,
    parse_filter_query,
)
from publicus_backend.schemas.grants import ExportRequest
from publicus_backend.services.grants import (
    GRANTS_RESOURCE_ID,
    NIL_RESOURCE_ID,
    SEARCH_BASE_URL,
    build_client,
    datastore_page,
    discover,
    package_show,
    poll_export,
    resource_by_id,
    start_export,
)


router = APIRouter(prefix="/api/grants", tags=["grants"])

ALLOWED_GRANTS_FILTER_FIELDS = {
    "_id",
    "agreement_end_date",
    "agreement_start_date",
    "agreement_title_en",
    "agreement_type",
    "agreement_value",
    "owner_org",
    "owner_org_title",
    "prog_name_en",
    "recipient_city",
    "recipient_legal_name",
    "recipient_province",
    "ref_number",
}
MAX_GRANTS_QUERY_LENGTH = 500
MAX_GRANTS_FILTERS = 12
MAX_GRANTS_FILTER_VALUE_LENGTH = 500


def normalize_grants_sort(sort: str | None) -> str | None:
    if not sort or sort == "score":
        return None
    if sort == "amount":
        return "agreement_value desc"
    if sort == "newest":
        return "agreement_start_date desc"

    allowed_fields = {"agreement_start_date", "agreement_end_date", "agreement_value", "_id"}
    parts = sort.split()
    if len(parts) == 2 and parts[0] in allowed_fields and parts[1].lower() in SORT_ORDERS:
        return f"{parts[0]} {parts[1].lower()}"

    raise HTTPException(status_code=400, detail="sort must be score, amount, newest, or an allowed CKAN sort expression.")


def resolve_grants_resource(resource: str) -> str:
    if resource in {"grants", GRANTS_RESOURCE_ID}:
        return GRANTS_RESOURCE_ID
    if resource in {"nil", "nil-report", NIL_RESOURCE_ID}:
        return NIL_RESOURCE_ID
    raise HTTPException(status_code=400, detail="resource must be 'grants' or 'nil'.")


def normalize_grants_query(q: str | None) -> str | None:
    if q is not None and len(q) > MAX_GRANTS_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail=f"q must be {MAX_GRANTS_QUERY_LENGTH} characters or fewer.")
    return q


def parse_grants_filter_query(filter_values: list[str]) -> dict[str, str] | None:
    if len(filter_values) > MAX_GRANTS_FILTERS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_GRANTS_FILTERS} filters are allowed.")

    filters = parse_filter_query(filter_values)
    if not filters:
        return None

    for key, value in filters.items():
        if key not in ALLOWED_GRANTS_FILTER_FIELDS:
            allowed = ", ".join(sorted(ALLOWED_GRANTS_FILTER_FIELDS))
            raise HTTPException(status_code=400, detail=f"filter key must be one of: {allowed}.")
        if len(value) > MAX_GRANTS_FILTER_VALUE_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"filter value for {key} must be {MAX_GRANTS_FILTER_VALUE_LENGTH} characters or fewer.",
            )

    return filters


def record_date_value(record: dict[str, Any], date_field: str) -> str:
    value = record.get(date_field)
    return value if isinstance(value, str) else ""


def sorted_datastore_total(client: httpx.Client, resource_id: str, date_field: str) -> tuple[int, list[dict[str, Any]]]:
    result = datastore_page(
        client,
        resource_id,
        limit=1,
        offset=0,
        q=None,
        filters=None,
        sort=f"{date_field} asc",
    )
    return int(result.get("total") or 0), result.get("fields", [])


def first_offset_for_date(
    client: httpx.Client,
    resource_id: str,
    *,
    date_field: str,
    target_date: str,
    total: int,
) -> int:
    low = 0
    high = total

    while low < high:
        midpoint = (low + high) // 2
        result = datastore_page(
            client,
            resource_id,
            limit=1,
            offset=midpoint,
            q=None,
            filters=None,
            sort=f"{date_field} asc",
        )
        records = result.get("records", [])
        if not records:
            high = midpoint
            continue

        if record_date_value(records[0], date_field) >= target_date:
            high = midpoint
        else:
            low = midpoint + 1

    return low


@router.get("/discover")
def grants_discover(
    query_string: str = Query(
        default="",
        max_length=2000,
        description="Optional website query string, for example 'year=2025&owner_org=nrc-cnrc'.",
    ),
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        with build_client(timeout) as client:
            return discover(client, normalize_query_string(query_string))
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/resources")
def grants_resources(timeout: float = Query(default=60.0, ge=5.0, le=300.0)) -> dict[str, Any]:
    try:
        with build_client(timeout) as client:
            package = package_show(client)
            return {
                "dataset_id": package["id"],
                "title": package.get("title"),
                "metadata_modified": package.get("metadata_modified"),
                "resources": package.get("resources", []),
            }
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/csv-url")
def grants_csv_url(
    resource: str = Query(default="grants", description="'grants', 'nil', or a CKAN resource id."),
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        resource_id = resolve_grants_resource(resource)
        with build_client(timeout) as client:
            package = package_show(client)
            dataset_resource = resource_by_id(package, resource_id)
            return {
                "resource_id": resource_id,
                "name": dataset_resource.get("name"),
                "url": dataset_resource.get("url"),
                "size": dataset_resource.get("size"),
                "hash": dataset_resource.get("hash"),
                "last_modified": dataset_resource.get("last_modified"),
            }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("")
def list_grants(
    resource: str = Query(default="grants", description="'grants', 'nil', or a CKAN resource id."),
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, description="CKAN full-text search query."),
    year: int | None = Query(
        default=None,
        ge=1800,
        le=2200,
        description="Optional calendar year searched against agreement_start_date.",
    ),
    sort: str | None = Query(
        default=None,
        description="'score', 'amount', 'newest', or an allowed CKAN sort expression.",
    ),
    include_total: bool = Query(default=True, description="Set false for faster filtered pages when total is not needed."),
    filter_values: Annotated[
        list[str],
        Query(
            alias="filter",
            description="Exact filter as KEY=VALUE. Repeat for multiple filters.",
        ),
    ] = [],
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        resource_id = resolve_grants_resource(resource)
        filters = parse_grants_filter_query(filter_values)
        query: str | dict[str, str] | None = normalize_grants_query(q)
        if year is not None:
            query = {"agreement_start_date": str(year)}
        datastore_sort = normalize_grants_sort(sort)
        with build_client(timeout) as client:
            result = datastore_page(
                client,
                resource_id,
                limit=limit,
                offset=offset,
                q=query,
                filters=filters,
                sort=datastore_sort,
                include_total=include_total,
            )
            records = result.get("records", [])
            return {
                "resource_id": resource_id,
                "limit": result.get("limit", limit),
                "offset": offset,
                "count": len(records),
                "total": result.get("total"),
                "filters": filters or {},
                "year": year,
                "q": query,
                "sort": datastore_sort,
                "records": records,
                "fields": result.get("fields", []),
                "links": result.get("_links", {}),
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/first/{count}")
def first_grants(
    count: int = PathParam(ge=1, le=5000, description="Number of grants to return from the beginning of the dataset."),
    resource: str = Query(default="grants", description="'grants', 'nil', or a CKAN resource id."),
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        resource_id = resolve_grants_resource(resource)
        with build_client(timeout) as client:
            result = datastore_page(
                client,
                resource_id,
                limit=count,
                offset=0,
                q=None,
                filters=None,
            )
            records = result.get("records", [])
            return {
                "resource_id": resource_id,
                "requested": count,
                "offset": 0,
                "count": len(records),
                "total": result.get("total"),
                "records": records,
                "fields": result.get("fields", []),
                "links": result.get("_links", {}),
            }
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/calendar-year/{year}")
@router.get("/by-calendar-year/{year}")
def grants_by_calendar_year(
    year: int = PathParam(ge=1800, le=2200, description="Calendar year based on the selected date field."),
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0, description="Offset within the matching calendar-year slice."),
    order: str = Query(default="asc", description="'asc' for oldest first in the year, 'desc' for newest first."),
    date_field: str = Query(
        default="agreement_start_date",
        description="Date field used for the calendar year: agreement_start_date, agreement_end_date, or amendment_date.",
    ),
    resource: str = Query(default="grants", description="'grants', 'nil', or a CKAN resource id."),
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        sort_order = normalize_sort_order(order)
        calendar_date_field = normalize_calendar_date_field(date_field)
        start_date, end_date = calendar_year_range(year)
        resource_id = resolve_grants_resource(resource)

        with build_client(timeout) as client:
            total_records, fields = sorted_datastore_total(client, resource_id, calendar_date_field)
            lower_offset = first_offset_for_date(
                client,
                resource_id,
                date_field=calendar_date_field,
                target_date=start_date,
                total=total_records,
            )
            upper_offset = first_offset_for_date(
                client,
                resource_id,
                date_field=calendar_date_field,
                target_date=end_date,
                total=total_records,
            )
            matching_total = max(0, upper_offset - lower_offset)

            if offset >= matching_total:
                records: list[dict[str, Any]] = []
                links = {}
            else:
                page_limit = min(limit, matching_total - offset)
                if sort_order == "asc":
                    datastore_offset = lower_offset + offset
                else:
                    datastore_offset = (total_records - upper_offset) + offset

                result = datastore_page(
                    client,
                    resource_id,
                    limit=page_limit,
                    offset=datastore_offset,
                    q=None,
                    filters=None,
                    sort=f"{calendar_date_field} {sort_order}",
                )
                records = result.get("records", [])
                fields = result.get("fields", fields)
                links = result.get("_links", {})

            return {
                "resource_id": resource_id,
                "year": year,
                "date_field": calendar_date_field,
                "start_date": start_date,
                "end_date_exclusive": end_date,
                "sort": f"{calendar_date_field} {sort_order}",
                "limit": limit,
                "offset": offset,
                "count": len(records),
                "total": matching_total,
                "records": records,
                "fields": fields,
                "links": links,
                "strategy": "Uses CKAN datastore_search sorted by ISO date text and binary-searches API offsets for the calendar-year range.",
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/by-reference/{ref_number}")
def grant_by_reference(
    ref_number: str,
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    try:
        with build_client(timeout) as client:
            result = datastore_page(
                client,
                GRANTS_RESOURCE_ID,
                limit=1,
                offset=0,
                q=None,
                filters={"ref_number": ref_number},
            )
            records = result.get("records", [])
            if not records:
                raise HTTPException(status_code=404, detail=f"No grant found for ref_number={ref_number!r}.")
            return {
                "resource_id": GRANTS_RESOURCE_ID,
                "total": result.get("total"),
                "record": records[0],
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise api_error(exc) from exc


@router.post("/export")
def create_export(request: ExportRequest) -> dict[str, Any]:
    try:
        with build_client(request.timeout) as client:
            task = start_export(client, normalize_query_string(request.query_string))
            payload: dict[str, Any] = {
                "task_id": task.task_id,
                "download_page_url": task.download_page_url,
                "status_url": task.status_url,
            }

            if request.wait:
                status = poll_export(client, task, request.poll_interval, request.timeout)
                payload["result"] = status
                file_url = status.get("file_url")
                if file_url:
                    payload["file_url"] = urljoin(SEARCH_BASE_URL, file_url)

            return payload
    except Exception as exc:
        raise api_error(exc) from exc


@router.get("/export/{task_id}")
def get_export_status(
    task_id: str,
    timeout: float = Query(default=60.0, ge=5.0, le=300.0),
) -> dict[str, Any]:
    status_url = f"{SEARCH_BASE_URL}/search-results/en/grants/{task_id}"
    try:
        with build_client(timeout) as client:
            response = client.get(status_url, headers={"Accept": "application/json"})
            if response.status_code not in {200, 202}:
                response.raise_for_status()
            payload = response.json()
            file_url = payload.get("file_url")
            if file_url:
                payload["file_url"] = urljoin(SEARCH_BASE_URL, file_url)
            payload["task_id"] = task_id
            payload["status_url"] = status_url
            return payload
    except Exception as exc:
        raise api_error(exc) from exc
