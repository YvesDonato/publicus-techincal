from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from publicus_backend.core.errors import api_error
from publicus_backend.schemas.profile_copilot import ProfileCopilotExtractRequest
from publicus_backend.services.profile_copilot import ProfileCopilotUnavailable, extract_company_profile


router = APIRouter(prefix="/api/company-profile/copilot", tags=["company-profile-copilot"])


@router.post("/extract")
def extract_profile(request: ProfileCopilotExtractRequest) -> dict[str, Any]:
    try:
        return extract_company_profile(
            answers=request.answers,
            current_profile=request.current_profile,
            timeout=request.timeout,
        )
    except ProfileCopilotUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise api_error(exc) from exc
