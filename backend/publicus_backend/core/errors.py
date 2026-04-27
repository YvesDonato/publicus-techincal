from __future__ import annotations

import httpx
from fastapi import HTTPException


def api_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502,
            detail={
                "message": "Upstream API returned an error.",
                "status_code": exc.response.status_code,
                "url": str(exc.request.url),
                "body": exc.response.text[:1000],
            },
        )
    if isinstance(exc, httpx.RequestError):
        return HTTPException(
            status_code=502,
            detail={
                "message": "Could not reach upstream API.",
                "url": str(exc.request.url) if exc.request else None,
            },
        )
    if isinstance(exc, TimeoutError):
        return HTTPException(status_code=504, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))

