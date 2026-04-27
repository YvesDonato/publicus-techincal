from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from publicus_backend.services.embeddings import cosine_similarity, embed_texts, vector_literal


SOURCE_ALIASES = {
    "benefits": "business-benefits",
    "business_benefits": "business-benefits",
    "business-benefits": "business-benefits",
    "grants": "grants",
    "grants-contributions": "grants",
}
IDENTITY_FIELDS = [
    "_semantic_client_id",
    "ref_number",
    "id",
    "_id",
    "record_id",
    "project_id",
    "application_id",
    "token",
    "reference",
    "url",
]
TITLE_FIELDS = [
    "title",
    "title_en",
    "project_title",
    "project_name",
    "name",
    "recipient_legal_name",
    "organization_name",
    "applicant_name",
    "agreement_title_en",
]
DESCRIPTION_FIELDS = [
    "description",
    "description_en",
    "short_description",
    "program",
    "program_name",
    "program_name_en",
    "funding_program",
    "prog_name_en",
    "prog_purpose_en",
    "expected_results_en",
    "category",
    "sector",
    "industry",
    "status",
]


@dataclass(frozen=True)
class SemanticRecord:
    record_id: str
    source_id: str
    title: str
    content: str
    metadata: dict[str, Any]
    record: dict[str, Any]


def normalize_source(source: str) -> str:
    normalized = source.strip().lower()
    if normalized not in SOURCE_ALIASES:
        raise ValueError("source must be grants or business-benefits.")

    return SOURCE_ALIASES[normalized]


def score_semantic_records(
    *,
    profile: dict[str, Any],
    records: list[dict[str, Any]],
    source: str,
    rule_scores: dict[str, float],
    rule_weight: float,
    use_vector_cache: bool,
    timeout: float,
) -> dict[str, Any]:
    normalized_source = normalize_source(source)
    semantic_records = [build_semantic_record(record, normalized_source, index) for index, record in enumerate(records)]
    profile_text = profile_to_text(profile)
    embeddings, provider = embed_texts([profile_text, *[record.content for record in semantic_records]], timeout=timeout)
    profile_embedding = embeddings[0]
    record_embeddings = embeddings[1:]
    semantic_weight = 1.0 - rule_weight
    matches = []

    for item, embedding in zip(semantic_records, record_embeddings):
        similarity = cosine_similarity(profile_embedding, embedding)
        semantic_score = bounded_score((similarity + 1.0) * 50.0)
        rule_score = read_rule_score(rule_scores, item)
        combined_score = (
            bounded_score(rule_score * rule_weight + semantic_score * semantic_weight)
            if rule_score is not None
            else semantic_score
        )
        matches.append(
            {
                "record_id": item.record_id,
                "source": normalized_source,
                "source_id": item.source_id,
                "title": item.title,
                "semantic_score": semantic_score,
                "rule_score": rule_score,
                "combined_score": combined_score,
                "similarity": round(similarity, 6),
                "reasons": semantic_reasons(semantic_score),
            }
        )

    vector_store = "disabled"
    if use_vector_cache:
        vector_store = upsert_embeddings(normalized_source, semantic_records, record_embeddings)

    return {
        "source": normalized_source,
        "provider": provider,
        "vector_store": vector_store,
        "rule_weight": rule_weight,
        "semantic_weight": semantic_weight,
        "count": len(matches),
        "matches": matches,
    }


def search_semantic_index(
    *,
    profile: dict[str, Any],
    source: str | None,
    limit: int,
    timeout: float,
) -> dict[str, Any]:
    config = supabase_config()
    if config is None:
        return {
            "provider": "none",
            "vector_store": "not_configured",
            "count": 0,
            "matches": [],
        }

    normalized_source = normalize_source(source) if source else None
    embeddings, provider = embed_texts([profile_to_text(profile)], timeout=timeout)
    payload = {
        "query_embedding": vector_literal(embeddings[0]),
        "match_source": normalized_source,
        "match_count": limit,
    }

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        response = client.post(
            f"{config['url']}/rest/v1/rpc/match_opportunities",
            headers=supabase_headers(config["key"]),
            json=payload,
        )
        response.raise_for_status()
        matches = response.json()

    return {
        "provider": provider,
        "vector_store": "supabase",
        "count": len(matches) if isinstance(matches, list) else 0,
        "matches": matches if isinstance(matches, list) else [],
    }


def build_semantic_record(record: dict[str, Any], source: str, index: int) -> SemanticRecord:
    source_id = record_source_id(record, index)
    content = record_to_text(record)
    title = field_value(record, TITLE_FIELDS) or "Funding opportunity"
    record_id = f"{source}:{source_id}"
    return SemanticRecord(
        record_id=record_id,
        source_id=source_id,
        title=title,
        content=content,
        metadata={
            "title": title,
            "description": field_value(record, DESCRIPTION_FIELDS),
            "content_hash": content_hash(content),
        },
        record=record,
    )


def profile_to_text(profile: dict[str, Any]) -> str:
    activities = profile.get("activities")
    activity_text = ""
    if isinstance(activities, dict):
        activity_text = " ".join(key for key, value in activities.items() if value is True)

    fields = [
        "legalEntityName",
        "doingBusinessAs",
        "province",
        "city",
        "companyType",
        "employeeRange",
        "industry",
        "subSector",
        "keywords",
        "fundingNeed",
    ]
    parts = [str(profile.get(field, "")) for field in fields]
    parts.append(activity_text)
    return " ".join(part for part in parts if part.strip())


def record_to_text(record: dict[str, Any]) -> str:
    prioritized = []
    for field in [*TITLE_FIELDS, *DESCRIPTION_FIELDS]:
        value = record.get(field)
        if value is not None:
            prioritized.append(f"{field} {value_to_text(value)}")

    all_values = " ".join(f"{key} {value_to_text(value)}" for key, value in record.items() if not key.startswith("_semantic"))
    return " ".join([*prioritized, all_values])


def record_source_id(record: dict[str, Any], index: int) -> str:
    for field in IDENTITY_FIELDS:
        value = record.get(field)
        if value is not None and str(value).strip():
            return f"{field}:{str(value).strip()}"

    return f"hash:{content_hash(json.dumps(record, sort_keys=True, default=str))}:{index}"


def read_rule_score(rule_scores: dict[str, float], record: SemanticRecord) -> float | None:
    value = rule_scores.get(record.record_id) or rule_scores.get(record.source_id)
    if value is None:
        raw_value = record.record.get("_rule_score")
        value = raw_value if isinstance(raw_value, int | float) else None

    if value is None:
        return None

    return bounded_score(float(value))


def field_value(record: dict[str, Any], fields: list[str]) -> str | None:
    lower_keys = {key.lower(): key for key in record}
    for field in fields:
        key = lower_keys.get(field.lower())
        if not key:
            continue
        value = record.get(key)
        if value is not None and str(value).strip():
            return value_to_text(value)

    return None


def value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(value_to_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {value_to_text(item)}" for key, item in value.items())
    return str(value)


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def semantic_reasons(score: int) -> list[str]:
    if score >= 80:
        return ["Semantic similarity strongly supports this match."]
    if score >= 60:
        return ["Semantic similarity supports this match."]
    if score >= 45:
        return ["Semantic similarity is moderate; review eligibility details."]
    return ["Semantic similarity is weak compared with the company profile."]


def bounded_score(value: float) -> int:
    return max(0, min(100, round(value)))


def supabase_config() -> dict[str, str] | None:
    url = (os.getenv("SUPABASE_URL") or os.getenv("PUBLIC_SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None

    return {"url": url, "key": key}


def supabase_headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "authorization": f"Bearer {key}",
        "content-type": "application/json",
    }


def upsert_embeddings(source: str, records: list[SemanticRecord], embeddings: list[list[float]]) -> str:
    config = supabase_config()
    if config is None:
        return "not_configured"

    rows = [
        {
            "source": source,
            "source_id": record.source_id,
            "title": record.title,
            "body": record.content,
            "metadata": record.metadata,
            "content_hash": record.metadata["content_hash"],
            "embedding": vector_literal(embedding),
        }
        for record, embedding in zip(records, embeddings)
    ]
    if not rows:
        return "no_records"

    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = client.post(
                f"{config['url']}/rest/v1/opportunity_embeddings?on_conflict=source,source_id",
                headers={
                    **supabase_headers(config["key"]),
                    "prefer": "resolution=merge-duplicates,return=minimal",
                },
                json=rows,
            )
            response.raise_for_status()
    except Exception:
        return "write_failed"

    return "supabase"
