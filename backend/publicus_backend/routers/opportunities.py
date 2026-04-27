from __future__ import annotations

from fastapi import APIRouter, HTTPException

from publicus_backend.core.errors import api_error
from publicus_backend.schemas.opportunity_analysis import (
    OpportunityAnalysisRequest,
    OpportunityAnalysisResponse,
    OpportunityFitJudgeRequest,
    OpportunityFitJudgeResponse,
)
from publicus_backend.services.opportunity_analysis import OpportunityAnalysisUnavailable, analyze_opportunity, judge_opportunity_fits


router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.post("/analyze", response_model=OpportunityAnalysisResponse)
def analyze_opportunity_match(request: OpportunityAnalysisRequest) -> dict[str, object]:
    try:
        return analyze_opportunity(
            profile=request.profile,
            opportunity=request.opportunity,
            match=request.match,
            timeout=request.timeout,
        )
    except OpportunityAnalysisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise api_error(exc) from exc


@router.post("/judge-fit", response_model=OpportunityFitJudgeResponse)
def judge_opportunity_match_fit(request: OpportunityFitJudgeRequest) -> dict[str, object]:
    try:
        return judge_opportunity_fits(
            profile=request.profile,
            opportunities=request.opportunities,
            timeout=request.timeout,
        )
    except OpportunityAnalysisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise api_error(exc) from exc
