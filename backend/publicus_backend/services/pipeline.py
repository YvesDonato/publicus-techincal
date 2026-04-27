from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import httpx

from publicus_backend.services import business_benefits, grants


PipelineSource = Literal["grants", "business-benefits"]

SOURCE_ALIASES: dict[str, PipelineSource] = {
    "grant": "grants",
    "grants": "grants",
    "open-canada-grants": "grants",
    "open_canada_grants": "grants",
    "business-benefits": "business-benefits",
    "business_benefits": "business-benefits",
    "benefits": "business-benefits",
    "bbf": "business-benefits",
}
SUPPORTED_SOURCES: tuple[PipelineSource, ...] = ("grants", "business-benefits")
MAX_QUERY_LENGTH = 250
MAX_LIMIT = 5000
MAX_INGEST_RECORDS = 25000
DEFAULT_INGEST_RECORDS = 1000
SUPABASE_REST_SUFFIX = "/rest/v1"


class PipelineConfigError(RuntimeError):
    pass


class PipelineSourceError(ValueError):
    pass


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    service_role_key: str


def normalize_source(source: str) -> PipelineSource:
    normalized = source.strip().lower().replace("_", "-")
    resolved = SOURCE_ALIASES.get(normalized)
    if not resolved:
        allowed = ", ".join(SUPPORTED_SOURCES)
        raise PipelineSourceError(f"source must be one of: {allowed}.")
    return resolved


def supabase_config_from_env() -> SupabaseConfig:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise PipelineConfigError(
            "Pipeline storage is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return SupabaseConfig(url=url, service_role_key=key)


def is_configured() -> bool:
    try:
        supabase_config_from_env()
    except PipelineConfigError:
        return False
    return True


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def stable_content_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_text(value: Any, *, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()
    if not text:
        return None
    if max_length is not None:
        return text[:max_length]
    return text


def clean_url(value: Any, *, fallback: str | None = None) -> str | None:
    text = clean_text(value, max_length=2048)
    if text and re.match(r"^https?://", text, re.IGNORECASE):
        return text
    return fallback


def parse_date(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", text):
        return text.replace("/", "-")
    return None


def parse_amount(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    normalized = re.sub(r"[^0-9.\-]", "", text)
    if not normalized:
        return None
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    if amount < 0:
        return None
    return f"{amount.quantize(Decimal('0.01'))}"


def source_id_from_record(record: dict[str, Any], candidates: Iterable[str]) -> str:
    for key in candidates:
        value = clean_text(record.get(key), max_length=512)
        if value:
            return value
    return stable_content_hash(record)[:32]


def normalize_grant_record(record: dict[str, Any], *, ingestion_run_id: str | None) -> dict[str, Any]:
    source_id = source_id_from_record(record, ("ref_number", "_id", "id"))
    title = clean_text(record.get("agreement_title_en"), max_length=500) or clean_text(
        record.get("prog_name_en"), max_length=500
    )
    end_date = parse_date(record.get("agreement_end_date"))
    is_active = True
    if end_date:
        is_active = end_date >= date.today().isoformat()

    normalized = {
        "ingestion_run_id": ingestion_run_id,
        "source": "grants",
        "source_id": source_id,
        "source_url": None,
        "resource_metadata": {
            "dataset_id": grants.DATASET_ID,
            "resource_id": grants.GRANTS_RESOURCE_ID,
        },
        "raw_record": record,
        "title": title or "",
        "sponsor": clean_text(record.get("owner_org_title") or record.get("owner_org"), max_length=300),
        "description": clean_text(record.get("description_en") or record.get("prog_name_en")),
        "province": clean_text(record.get("recipient_province"), max_length=120),
        "city": clean_text(record.get("recipient_city"), max_length=160),
        "amount": parse_amount(record.get("agreement_value")),
        "start_date": parse_date(record.get("agreement_start_date")),
        "end_date": end_date,
        "deadline_date": None,
        "status": clean_text(record.get("agreement_type"), max_length=300),
        "is_active": is_active,
        "content_hash": stable_content_hash(record),
        "fetched_at": utc_now_iso(),
    }
    return normalized


def normalize_business_benefit_record(record: dict[str, Any], *, ingestion_run_id: str | None) -> dict[str, Any]:
    source_id = source_id_from_record(record, ("id", "dov_id", "_id", "title"))
    title = clean_text(record.get("title") or record.get("title_en"), max_length=500)
    status = clean_text(record.get("status"), max_length=300)
    is_active = not status or status.lower() not in {"inactive", "closed", "expired"}

    normalized = {
        "ingestion_run_id": ingestion_run_id,
        "source": "business-benefits",
        "source_id": source_id,
        "source_url": clean_url(record.get("url") or record.get("program_url"), fallback=business_benefits.BUSINESS_BENEFITS_PAGE),
        "resource_metadata": {
            "dataset_id": business_benefits.BUSINESS_BENEFITS_DATASET_ID,
        },
        "raw_record": record,
        "title": title or "",
        "sponsor": clean_text(record.get("organization") or record.get("department"), max_length=300),
        "description": clean_text(record.get("description") or record.get("program")),
        "province": clean_text(record.get("province"), max_length=120),
        "city": clean_text(record.get("city"), max_length=160),
        "amount": parse_amount(record.get("amount")),
        "start_date": parse_date(record.get("start_date")),
        "end_date": parse_date(record.get("end_date")),
        "deadline_date": parse_date(record.get("deadline_date") or record.get("deadline")),
        "status": status,
        "is_active": is_active,
        "content_hash": stable_content_hash(record),
        "fetched_at": utc_now_iso(),
    }
    return normalized


class SupabasePostgrest:
    def __init__(self, config: SupabaseConfig, *, timeout: float = 60.0) -> None:
        self.base_url = f"{config.url}{SUPABASE_REST_SUFFIX}"
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=30.0),
            headers={
                "apikey": config.service_role_key,
                "Authorization": f"Bearer {config.service_role_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> SupabasePostgrest:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def create_run(self, source: PipelineSource, metadata: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/ingestion_runs",
            headers={"Prefer": "return=representation"},
            json={"source": source, "status": "running", "metadata": metadata},
        )
        response.raise_for_status()
        return response.json()[0]

    def finish_run(
        self,
        run_id: str,
        *,
        status: Literal["succeeded", "failed"],
        records_seen: int,
        records_upserted: int,
        records_deactivated: int,
        records_failed: int,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "status": status,
            "completed_at": utc_now_iso(),
            "records_seen": records_seen,
            "records_upserted": records_upserted,
            "records_deactivated": records_deactivated,
            "records_failed": records_failed,
            "error_message": error_message,
        }
        response = self.client.patch(
            f"{self.base_url}/ingestion_runs",
            params={"id": f"eq.{run_id}"},
            headers={"Prefer": "return=representation"},
            json=payload,
        )
        response.raise_for_status()
        items = response.json()
        return items[0] if items else payload

    def upsert_records(self, records: list[dict[str, Any]], *, chunk_size: int = 500) -> int:
        if not records:
            return 0
        upserted = 0
        for index in range(0, len(records), chunk_size):
            chunk = records[index : index + chunk_size]
            response = self.client.post(
                f"{self.base_url}/source_records",
                params={"on_conflict": "source,source_id"},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json=chunk,
            )
            response.raise_for_status()
            upserted += len(chunk)
        return upserted

    def deactivate_missing(self, source: PipelineSource, seen_source_ids: set[str], *, chunk_size: int = 100) -> int:
        current_records = self.list_records(
            source=source,
            limit=10000,
            offset=0,
            active_only=True,
            q=None,
            select="id,source_id",
        )["records"]
        missing_ids = [record["id"] for record in current_records if record.get("source_id") not in seen_source_ids]
        deactivated = 0
        for index in range(0, len(missing_ids), chunk_size):
            chunk = missing_ids[index : index + chunk_size]
            response = self.client.patch(
                f"{self.base_url}/source_records",
                params={"id": f"in.({','.join(chunk)})"},
                headers={"Prefer": "return=minimal"},
                json={"is_active": False, "fetched_at": utc_now_iso()},
            )
            response.raise_for_status()
            deactivated += len(chunk)
        return deactivated

    def list_records(
        self,
        *,
        source: PipelineSource | None,
        limit: int,
        offset: int,
        active_only: bool,
        q: str | None,
        select: str = "*",
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {
            "select": select,
            "order": "updated_at.desc",
            "limit": limit,
            "offset": offset,
        }
        if source:
            params["source"] = f"eq.{source}"
        if active_only:
            params["is_active"] = "eq.true"
        if q:
            pattern = postgrest_ilike_pattern(q)
            params["or"] = f"(title.ilike.{pattern},sponsor.ilike.{pattern},description.ilike.{pattern})"

        response = self.client.get(
            f"{self.base_url}/source_records",
            params=params,
            headers={"Prefer": "count=exact"},
        )
        response.raise_for_status()
        return {
            "records": response.json(),
            "count": response_count(response),
            "limit": limit,
            "offset": offset,
        }

    def latest_runs(self, *, limit: int = 10) -> list[dict[str, Any]]:
        response = self.client.get(
            f"{self.base_url}/ingestion_runs",
            params={"select": "*", "order": "started_at.desc", "limit": limit},
        )
        response.raise_for_status()
        return response.json()


def postgrest_ilike_pattern(query: str) -> str:
    cleaned = clean_text(query, max_length=MAX_QUERY_LENGTH) or ""
    escaped = cleaned.replace("\\", "\\\\").replace("*", "\\*").replace(",", " ")
    return f"*{escaped}*"


def response_count(response: httpx.Response) -> int | None:
    content_range = response.headers.get("content-range")
    if not content_range or "/" not in content_range:
        return None
    total = content_range.rsplit("/", 1)[-1]
    if total == "*":
        return None
    try:
        return int(total)
    except ValueError:
        return None


def fetch_normalized_records(
    source: PipelineSource,
    *,
    ingestion_run_id: str | None,
    max_records: int,
    page_size: int,
    timeout: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if source == "grants":
        return fetch_grants_records(
            ingestion_run_id=ingestion_run_id,
            max_records=max_records,
            page_size=page_size,
            timeout=timeout,
        )
    return fetch_business_benefit_records(
        ingestion_run_id=ingestion_run_id,
        max_records=max_records,
        timeout=timeout,
    )


def fetch_grants_records(
    *,
    ingestion_run_id: str | None,
    max_records: int,
    page_size: int,
    timeout: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_records: list[dict[str, Any]] = []
    total: int | None = None
    with grants.build_client(timeout) as client:
        for page in grants.iter_datastore_pages(
            client,
            grants.GRANTS_RESOURCE_ID,
            page_size=page_size,
            start_offset=0,
            max_records=max_records,
            q=None,
            filters=None,
        ):
            total = int(page.get("total") or 0)
            for record in page.get("records", []):
                normalized_records.append(normalize_grant_record(record, ingestion_run_id=ingestion_run_id))

    return normalized_records, {
        "source_dataset": grants.DATASET_ID,
        "resource_id": grants.GRANTS_RESOURCE_ID,
        "upstream_total": total,
        "max_records": max_records,
        "full_snapshot": total is not None and len(normalized_records) >= total,
    }


def fetch_business_benefit_records(
    *,
    ingestion_run_id: str | None,
    max_records: int,
    timeout: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with business_benefits.build_client(timeout) as client:
        package = business_benefits.package_show(client)
        resource = business_benefits.latest_xlsx_resource(package)
        response = client.get(resource["url"])
        response.raise_for_status()
        raw_records = business_benefits.parse_programs_xlsx(response.content, max_records)

    normalized_records = [
        normalize_business_benefit_record(record, ingestion_run_id=ingestion_run_id) for record in raw_records
    ]
    return normalized_records, {
        "source_dataset": business_benefits.BUSINESS_BENEFITS_DATASET_ID,
        "resource_id": resource.get("id"),
        "resource_name": resource.get("name"),
        "source_url": resource.get("url"),
        "max_records": max_records,
        "full_snapshot": len(raw_records) < max_records,
    }


def ingest_source(
    source_value: str,
    *,
    max_records: int = DEFAULT_INGEST_RECORDS,
    page_size: int = 1000,
    timeout: float = 60.0,
) -> dict[str, Any]:
    source = normalize_source(source_value)
    max_records = min(max(max_records, 1), MAX_INGEST_RECORDS)
    page_size = min(max(page_size, 1), 5000)
    config = supabase_config_from_env()

    with SupabasePostgrest(config, timeout=timeout) as storage:
        run = storage.create_run(
            source,
            {
                "requested_max_records": max_records,
                "page_size": page_size,
                "started_by": "api",
            },
        )
        run_id = str(run["id"])
        try:
            records, source_metadata = fetch_normalized_records(
                source,
                ingestion_run_id=run_id,
                max_records=max_records,
                page_size=page_size,
                timeout=timeout,
            )
            for record in records:
                record["resource_metadata"] = {**record.get("resource_metadata", {}), **source_metadata}
            records_upserted = storage.upsert_records(records)
            seen_source_ids = {record["source_id"] for record in records}
            records_deactivated = (
                storage.deactivate_missing(source, seen_source_ids)
                if source_metadata.get("full_snapshot") is True
                else 0
            )
            finished = storage.finish_run(
                run_id,
                status="succeeded",
                records_seen=len(records),
                records_upserted=records_upserted,
                records_deactivated=records_deactivated,
                records_failed=0,
            )
            return {
                "run": finished,
                "source": source,
                "records_seen": len(records),
                "records_upserted": records_upserted,
                "records_deactivated": records_deactivated,
            }
        except Exception as exc:
            storage.finish_run(
                run_id,
                status="failed",
                records_seen=0,
                records_upserted=0,
                records_deactivated=0,
                records_failed=1,
                error_message=str(exc)[:2000],
            )
            raise


def pipeline_status(*, timeout: float = 30.0) -> dict[str, Any]:
    if not is_configured():
        return {
            "configured": False,
            "sources": list(SUPPORTED_SOURCES),
            "message": "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable pipeline storage.",
        }

    config = supabase_config_from_env()
    with SupabasePostgrest(config, timeout=timeout) as storage:
        runs = storage.latest_runs(limit=10)
    return {
        "configured": True,
        "sources": list(SUPPORTED_SOURCES),
        "latest_runs": runs,
    }


def query_records(
    *,
    source_value: str | None,
    limit: int,
    offset: int,
    active_only: bool,
    q: str | None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    source = normalize_source(source_value) if source_value else None
    if q is not None and len(q) > MAX_QUERY_LENGTH:
        raise ValueError(f"q must be {MAX_QUERY_LENGTH} characters or fewer.")
    limit = min(max(limit, 1), MAX_LIMIT)
    offset = max(offset, 0)
    config = supabase_config_from_env()
    with SupabasePostgrest(config, timeout=timeout) as storage:
        result = storage.list_records(
            source=source,
            limit=limit,
            offset=offset,
            active_only=active_only,
            q=q,
        )
    return {
        "source": source,
        "active_only": active_only,
        **result,
    }
