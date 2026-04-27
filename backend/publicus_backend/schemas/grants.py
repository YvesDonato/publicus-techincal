from __future__ import annotations

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    query_string: str = Field(
        default="",
        description="Website query string, for example 'year=2025&sort=agreement_value+desc'.",
    )
    wait: bool = Field(default=False, description="Poll the export task until it finishes.")
    poll_interval: float = Field(default=1.0, ge=0.25, le=30.0)
    timeout: float = Field(default=120.0, ge=5.0, le=1800.0)

