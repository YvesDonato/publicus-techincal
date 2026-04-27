from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


OpportunitySource = Literal["business-benefits", "grants"]
AnalysisConfidence = Literal["low", "medium", "high"]
OpportunityFit = Literal["strong", "possible", "weak"]


class OpportunityMatchContext(BaseModel):
    source: OpportunitySource = Field(default="business-benefits")
    title: str | None = Field(default=None, max_length=500)
    sponsor: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    deadline: str | None = Field(default=None, max_length=120)
    status_label: str | None = Field(default=None, max_length=120)
    match_score: float = Field(ge=0, le=100)
    semantic_score: float | None = Field(default=None, ge=0, le=100)
    rule_score: float | None = Field(default=None, ge=0, le=100)
    potential_funding: float | None = Field(default=None, ge=0)
    reasons: list[str] = Field(default_factory=list, max_length=12)
    risks: list[str] = Field(default_factory=list, max_length=12)
    next_actions: list[str] = Field(default_factory=list, max_length=12)


class OpportunityFitJudgment(BaseModel):
    record_ref: str
    fit: OpportunityFit
    should_show: bool
    confidence: AnalysisConfidence
    reason: str
    risk_notes: list[str]


class OpportunityAnalysisRequest(BaseModel):
    profile: dict[str, Any] = Field(description="Company profile used to score the opportunity.")
    opportunity: dict[str, Any] = Field(description="Raw active opportunity record.")
    match: OpportunityMatchContext
    fit_judgment: OpportunityFitJudgment | None = Field(
        default=None,
        description="Optional LLM fit-filter judgment that detailed analysis must respect.",
    )
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)


class OpportunityAnalysisResponse(BaseModel):
    fit: OpportunityFit
    should_show: bool
    fit_summary: str
    eligibility_flags: list[str]
    missing_company_info: list[str]
    application_steps: list[str]
    risk_notes: list[str]
    questions_to_answer: list[str]
    confidence: AnalysisConfidence
    provider: str


class OpportunityFitJudgeCandidate(BaseModel):
    record_ref: str = Field(min_length=1, max_length=500)
    opportunity: dict[str, Any] = Field(description="Raw active opportunity record.")
    match: OpportunityMatchContext


class OpportunityFitJudgeRequest(BaseModel):
    profile: dict[str, Any] = Field(description="Company profile used to judge the opportunity fit.")
    opportunities: list[OpportunityFitJudgeCandidate] = Field(default_factory=list, max_length=20)
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)


class OpportunityFitJudgeResponse(BaseModel):
    judgments: list[OpportunityFitJudgment]
    provider: str
    filter_available: bool
    unavailable_reason: str | None = None
