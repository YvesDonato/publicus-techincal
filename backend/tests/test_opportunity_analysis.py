from __future__ import annotations

import pytest

from publicus_backend.schemas.opportunity_analysis import (
    OpportunityComparisonSide,
    OpportunityFitJudgeCandidate,
    OpportunityFitJudgment,
    OpportunityMatchContext,
)
from publicus_backend.services.opportunity_analysis import (
    analyze_opportunity,
    compare_opportunities,
    judge_opportunity_fits,
    normalize_analysis_payload,
    normalize_comparison_payload,
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
    assert result["fit"] == "possible"
    assert result["should_show"] is True
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
    assert result["fit"] == "possible"
    assert result["should_show"] is True


def test_analyze_opportunity_respects_supplied_fit_judgment_without_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)

    result = analyze_opportunity(
        profile={"province": "ON"},
        opportunity={"title": "Test program"},
        match=OpportunityMatchContext(match_score=82, reasons=["Keyword overlap."]),
        fit_judgment=OpportunityFitJudgment(
            record_ref="benefit-1",
            fit="weak",
            should_show=False,
            confidence="high",
            reason="The program is for nonprofits, but the company is for-profit.",
            risk_notes=["Applicant type conflicts with the opportunity."],
        ),
        timeout=5.0,
    )

    assert result["provider"] == "local-fallback"
    assert result["fit"] == "weak"
    assert result["should_show"] is False
    assert result["confidence"] == "high"
    assert any("Applicant type conflicts" in note for note in result["risk_notes"])


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


def test_normalize_comparison_payload_uses_valid_recommendation_ref() -> None:
    left = OpportunityComparisonSide(
        record_ref="left-1",
        opportunity={"title": "Left program"},
        match=OpportunityMatchContext(title="Left program", match_score=82, potential_funding=100000),
    )
    right = OpportunityComparisonSide(
        record_ref="right-1",
        opportunity={"title": "Right program"},
        match=OpportunityMatchContext(title="Right program", match_score=64, potential_funding=250000),
    )

    result = normalize_comparison_payload(
        {
            "recommended_ref": "unknown-ref",
            "summary": "Choose the better first action.",
            "decision_factors": ["Strong fit."],
            "confidence": "high",
        },
        left=left,
        right=right,
    )

    assert result["recommended_ref"] == "left-1"
    assert result["summary"] == "Choose the better first action."
    assert result["decision_factors"] == ["Strong fit."]
    assert result["confidence"] == "high"


def test_compare_opportunities_uses_local_fallback_without_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)

    result = compare_opportunities(
        profile={"province": "ON"},
        left=OpportunityComparisonSide(
            record_ref="left-1",
            opportunity={"title": "Left program"},
            match=OpportunityMatchContext(title="Left program", match_score=78, potential_funding=100000),
        ),
        right=OpportunityComparisonSide(
            record_ref="right-1",
            opportunity={"title": "Right program"},
            match=OpportunityMatchContext(title="Right program", match_score=58, potential_funding=200000),
        ),
        timeout=5.0,
    )

    assert result["provider"] == "local-fallback"
    assert result["comparison_available"] is False
    assert result["recommended_ref"] == "left-1"
    assert result["decision_factors"]
