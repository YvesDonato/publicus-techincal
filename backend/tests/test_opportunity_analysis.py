from __future__ import annotations

import pytest

from publicus_backend.schemas.opportunity_analysis import OpportunityFitJudgeCandidate, OpportunityMatchContext
from publicus_backend.services.opportunity_analysis import (
    analyze_opportunity,
    judge_opportunity_fits,
    normalize_analysis_payload,
    normalize_fit_judgment_response,
)


def test_normalize_analysis_payload_bounds_and_confidence() -> None:
    result = normalize_analysis_payload(
        {
            "fit_summary": "  Strong match.  Verify the applicant rules. ",
            "eligibility_flags": ["Ontario signal", "Ontario signal", "", "SME language"],
            "missing_company_info": ["Official project budget"],
            "application_steps": ["Read the program guide"],
            "risk_notes": ["Deadline was not present"],
            "questions_to_answer": ["Is the project eligible?"],
            "confidence": 0.81,
        }
    )

    assert result["fit_summary"] == "Strong match. Verify the applicant rules."
    assert result["eligibility_flags"] == ["Ontario signal", "SME language"]
    assert result["confidence"] == "high"


def test_analyze_opportunity_uses_local_fallback_without_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)

    result = analyze_opportunity(
        profile={"province": "ON"},
        opportunity={"title": "Test program"},
        match=OpportunityMatchContext(match_score=75),
        timeout=5.0,
    )

    assert result["provider"] == "local-fallback"
    assert result["confidence"] == "high"


def test_normalize_fit_judgment_response_keeps_low_confidence_weak_visible() -> None:
    candidate = OpportunityFitJudgeCandidate(
        record_ref="candidate-1",
        opportunity={"title": "Test program"},
        match=OpportunityMatchContext(match_score=68, reasons=["Matches Ontario."]),
    )

    result = normalize_fit_judgment_response(
        {
            "judgments": [
                {
                    "record_ref": "candidate-1",
                    "fit": "weak",
                    "should_show": False,
                    "confidence": "low",
                    "reason": "Not enough evidence.",
                    "risk_notes": ["Eligibility is unclear."],
                }
            ]
        },
        [candidate],
    )

    assert result["filter_available"] is True
    assert result["judgments"][0]["fit"] == "possible"
    assert result["judgments"][0]["should_show"] is True


def test_judge_opportunity_fits_falls_back_without_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)

    result = judge_opportunity_fits(
        profile={"province": "ON"},
        opportunities=[
            OpportunityFitJudgeCandidate(
                record_ref="candidate-1",
                opportunity={"title": "Test program"},
                match=OpportunityMatchContext(match_score=40, reasons=["Some profile signal."]),
            )
        ],
        timeout=5.0,
    )

    assert result["provider"] == "local-fallback"
    assert result["filter_available"] is False
    assert result["judgments"][0]["should_show"] is True
