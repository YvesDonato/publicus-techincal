from __future__ import annotations

from urllib.parse import parse_qsl, urlencode

from fastapi import HTTPException


CALENDAR_YEAR_DATE_FIELDS = {"agreement_start_date", "agreement_end_date", "amendment_date"}
SORT_ORDERS = {"asc", "desc"}


def normalize_query_string(query_string: str) -> str:
    if not query_string:
        return ""
    return urlencode(parse_qsl(query_string, keep_blank_values=True))


def parse_filter_query(filters: list[str]) -> dict[str, str] | None:
    parsed: dict[str, str] = {}
    for value in filters:
        if "=" not in value:
            raise HTTPException(status_code=400, detail=f"Expected filter as KEY=VALUE, got {value!r}.")
        key, item = value.split("=", 1)
        if not key:
            raise HTTPException(status_code=400, detail=f"Expected non-empty filter key, got {value!r}.")
        parsed[key] = item
    return parsed or None


def normalize_sort_order(order: str) -> str:
    normalized = order.lower()
    if normalized not in SORT_ORDERS:
        raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'.")
    return normalized


def normalize_calendar_date_field(date_field: str) -> str:
    if date_field not in CALENDAR_YEAR_DATE_FIELDS:
        allowed = ", ".join(sorted(CALENDAR_YEAR_DATE_FIELDS))
        raise HTTPException(status_code=400, detail=f"date_field must be one of: {allowed}.")
    return date_field


def calendar_year_range(year: int) -> tuple[str, str]:
    return f"{year:04d}-01-01", f"{year + 1:04d}-01-01"

