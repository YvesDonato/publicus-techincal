from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import HTTPException


SENSITIVE_QUERY_KEYS = {"api_key", "apikey", "key", "password", "secret", "token"}


def safe_url(url: httpx.URL | str | None) -> str | None:
    if url is None:
        return None

    parts = urlsplit(str(url))
    query = urlencode(
        [
            (key, "[redacted]" if key.lower() in SENSITIVE_QUERY_KEYS else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def api_error(exc: Exception) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502,
            detail={
                "message": "Upstream API returned an error.",
                "status_code": exc.response.status_code,
                "url": safe_url(exc.request.url),
                "body": exc.response.text[:1000],
            },
        )
    if isinstance(exc, httpx.RequestError):
        return HTTPException(
            status_code=502,
            detail={
                "message": "Could not reach upstream API.",
                "url": safe_url(exc.request.url) if exc.request else None,
            },
        )
    if isinstance(exc, TimeoutError):
        return HTTPException(status_code=504, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))
