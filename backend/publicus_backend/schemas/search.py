from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SemanticSource = Literal["grants", "business-benefits", "business_benefits", "benefits", "grants-contributions"]


class SemanticScoreRequest(BaseModel):
    profile: dict[str, Any] = Field(description="Company profile used as the semantic query.")
    records: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=1000,
        description="Candidate grant or benefit records to score against the profile.",
    )
    source: SemanticSource = Field(default="business-benefits")
    rule_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Optional existing rule scores keyed by semantic record id or source id.",
    )
    rule_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    use_vector_cache: bool = Field(
        default=True,
        description="When Supabase service credentials are configured, upsert record embeddings into pgvector.",
    )
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)


class SemanticIndexSearchRequest(BaseModel):
    profile: dict[str, Any] = Field(description="Company profile used as the semantic query.")
    source: SemanticSource | None = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)
