from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from publicus_backend.core.errors import api_error
from publicus_backend.schemas.search import SemanticIndexSearchRequest, SemanticScoreRequest
from publicus_backend.services.semantic_search import score_semantic_records, search_semantic_index


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/semantic")
def semantic_score(request: SemanticScoreRequest) -> dict[str, Any]:
    try:
        return score_semantic_records(
            profile=request.profile,
            records=request.records,
            source=request.source,
            rule_scores=request.rule_scores,
            rule_weight=request.rule_weight,
            use_vector_cache=request.use_vector_cache,
            timeout=request.timeout,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise api_error(exc) from exc


@router.post("/semantic/index")
def semantic_index_search(request: SemanticIndexSearchRequest) -> dict[str, Any]:
    try:
        return search_semantic_index(
            profile=request.profile,
            source=request.source,
            limit=request.limit,
            timeout=request.timeout,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise api_error(exc) from exc
