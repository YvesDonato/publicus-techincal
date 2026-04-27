from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from publicus_backend.schemas.opportunity_analysis import OpportunityFitJudgeCandidate, OpportunityFitJudgment, OpportunityMatchContext


class OpportunityAnalysisUnavailable(RuntimeError):
    pass


MAX_JSON_CONTEXT_CHARS = 12000


def judge_opportunity_fits(
    *,
    profile: dict[str, Any],
    opportunities: list[OpportunityFitJudgeCandidate],
    timeout: float,
) -> dict[str, Any]:
    if not opportunities:
        return {
            "judgments": [],
            "provider": "none",
            "filter_available": False,
            "unavailable_reason": None,
        }

    api_key = google_api_key()
    if not api_key:
        return build_local_fit_judgment_response(
            opportunities=opportunities,
            unavailable_reason="Gemini is not configured, so FundRadar kept the existing ranked matches.",
        )

    try:
        payload = call_gemini_opportunity_analysis(
            prompt=build_fit_judgment_prompt(profile=profile, opportunities=opportunities),
            api_key=api_key,
            timeout=timeout,
        )
        parsed = parse_gemini_json(payload)
        return normalize_fit_judgment_response(parsed, opportunities)
    except (OpportunityAnalysisUnavailable, httpx.HTTPError) as exc:
        return build_local_fit_judgment_response(
            opportunities=opportunities,
            unavailable_reason=get_fit_judgment_unavailable_reason(exc),
        )


def analyze_opportunity(
    *,
    profile: dict[str, Any],
    opportunity: dict[str, Any],
    match: OpportunityMatchContext,
    fit_judgment: OpportunityFitJudgment | None = None,
    timeout: float,
) -> dict[str, Any]:
    api_key = google_api_key()
    if not api_key:
        return build_local_analysis(
            profile=profile,
            match=match,
            fit_judgment=fit_judgment,
            unavailable_reason="Gemini is not configured, so FundRadar used the scored match signals.",
        )

    try:
        payload = call_gemini_opportunity_analysis(
            prompt=build_opportunity_prompt(
                profile=profile,
                opportunity=opportunity,
                match=match,
                fit_judgment=fit_judgment,
            ),
            api_key=api_key,
            timeout=timeout,
        )
        parsed = parse_gemini_json(payload)
        normalized = normalize_analysis_payload(parsed, match=match, fit_judgment=fit_judgment)
        normalized["provider"] = "google"
        return normalized
    except (OpportunityAnalysisUnavailable, httpx.HTTPError) as exc:
        return build_local_analysis(
            profile=profile,
            match=match,
            fit_judgment=fit_judgment,
            unavailable_reason=get_gemini_unavailable_reason(exc),
        )


def call_gemini_opportunity_analysis(*, prompt: str, api_key: str, timeout: float) -> dict[str, Any]:
    model = os.getenv("PUBLICUS_GEMINI_GENERATION_MODEL", "gemini-3-flash-preview")
    model_path = model if model.startswith("models/") else f"models/{model}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
    request = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    }

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        response = client.post(
            url,
            params={"key": api_key},
            headers={"content-type": "application/json"},
            json=request,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise OpportunityAnalysisUnavailable(
                    "Gemini quota or rate limit was reached, so FundRadar used the scored match signals."
                ) from exc
            if exc.response.status_code in {401, 403}:
                raise OpportunityAnalysisUnavailable(
                    "Gemini rejected the configured API key or project permissions, so FundRadar used the scored match signals."
                ) from exc
            raise
        return response.json()


def get_gemini_unavailable_reason(exc: Exception) -> str:
    if isinstance(exc, OpportunityAnalysisUnavailable):
        return str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return "Gemini timed out, so FundRadar used the scored match signals."
    if isinstance(exc, httpx.RequestError):
        return "Gemini could not be reached, so FundRadar used the scored match signals."
    if isinstance(exc, httpx.HTTPStatusError):
        return f"Gemini returned HTTP {exc.response.status_code}, so FundRadar used the scored match signals."
    return "Gemini analysis was unavailable, so FundRadar used the scored match signals."


def get_fit_judgment_unavailable_reason(exc: Exception) -> str:
    if isinstance(exc, OpportunityAnalysisUnavailable):
        message = str(exc)
        return message.replace("used the scored match signals", "kept the existing ranked matches")
    if isinstance(exc, httpx.TimeoutException):
        return "Gemini timed out, so FundRadar kept the existing ranked matches."
    if isinstance(exc, httpx.RequestError):
        return "Gemini could not be reached, so FundRadar kept the existing ranked matches."
    if isinstance(exc, httpx.HTTPStatusError):
        return f"Gemini returned HTTP {exc.response.status_code}, so FundRadar kept the existing ranked matches."
    return "Gemini fit filtering was unavailable, so FundRadar kept the existing ranked matches."


def build_fit_judgment_prompt(*, profile: dict[str, Any], opportunities: list[OpportunityFitJudgeCandidate]) -> str:
    schema = {
        "judgments": [
            {
                "record_ref": "same opaque record_ref from the input",
                "fit": "strong | possible | weak",
                "should_show": "boolean",
                "confidence": "low | medium | high",
                "reason": "one short sentence",
                "risk_notes": ["short reasons to verify or why fit may be weak"],
            }
        ]
    }
    candidates = [
        {
            "record_ref": item.record_ref,
            "opportunity": compact_json(item.opportunity),
            "match": {
                "title": item.match.title,
                "sponsor": item.match.sponsor,
                "description": item.match.description,
                "deadline": item.match.deadline,
                "status_label": item.match.status_label,
                "match_score": item.match.match_score,
                "semantic_score": item.match.semantic_score,
                "rule_score": item.match.rule_score,
                "potential_funding": item.match.potential_funding,
                "reasons": item.match.reasons,
                "risks": item.match.risks,
                "next_actions": item.match.next_actions,
            },
        }
        for item in opportunities
    ]

    return (
        "You are FundRadar's second-stage fit judge for Canadian business funding opportunities.\n"
        "The app already produced prospective matches. Your job is to remove only clear poor fits for the supplied company profile.\n"
        "Use only the provided company profile, active opportunity records, and existing match context. Do not invent eligibility rules, "
        "deadlines, funding amounts, or application requirements. If a record is plausible but uncertain, set fit to possible and "
        "should_show to true. Use fit=weak and should_show=false only when the supplied evidence clearly conflicts with the profile "
        "or has no meaningful relationship to the company's location, applicant type, sector, activities, or funding need.\n"
        "Return one judgment for every input record_ref. Return only valid JSON.\n\n"
        f"Response shape:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"Company profile:\n{compact_json(profile)}\n\n"
        f"Candidate opportunities:\n{compact_json(candidates)}"
    )


def normalize_fit_judgment_response(
    payload: dict[str, Any],
    opportunities: list[OpportunityFitJudgeCandidate],
) -> dict[str, Any]:
    raw_judgments = payload.get("judgments")
    if not isinstance(raw_judgments, list):
        raw_judgments = []

    raw_by_ref = {
        str(item.get("record_ref", "")).strip(): item
        for item in raw_judgments
        if isinstance(item, dict) and str(item.get("record_ref", "")).strip()
    }
    judgments = []
    for opportunity in opportunities:
        raw = raw_by_ref.get(opportunity.record_ref)
        judgments.append(normalize_fit_judgment(raw, opportunity))

    return {
        "judgments": judgments,
        "provider": "google",
        "filter_available": True,
        "unavailable_reason": None,
    }


def normalize_fit_judgment(raw: dict[str, Any] | None, opportunity: OpportunityFitJudgeCandidate) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    fit = normalize_fit(raw.get("fit"), opportunity.match.match_score)
    confidence = normalize_confidence(raw.get("confidence"))
    should_show = raw.get("should_show")
    if not isinstance(should_show, bool):
        should_show = fit != "weak"

    if fit == "weak" and confidence == "low":
        fit = "possible"
        should_show = True

    reason = normalize_string(
        raw.get("reason"),
        local_fit_reason(opportunity.match),
        max_length=240,
    )
    risk_notes = normalize_string_list(raw.get("risk_notes"), max_items=4, max_length=180)

    return {
        "record_ref": opportunity.record_ref,
        "fit": fit,
        "should_show": should_show,
        "confidence": confidence,
        "reason": reason,
        "risk_notes": risk_notes,
    }


def normalize_fit(value: Any, score: float) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"strong", "possible", "weak"}:
        return normalized
    if score >= 78:
        return "strong"
    if score >= 45:
        return "possible"
    return "weak"


def build_local_fit_judgment_response(
    *,
    opportunities: list[OpportunityFitJudgeCandidate],
    unavailable_reason: str,
) -> dict[str, Any]:
    return {
        "judgments": [build_local_fit_judgment(item, unavailable_reason) for item in opportunities],
        "provider": "local-fallback",
        "filter_available": False,
        "unavailable_reason": unavailable_reason,
    }


def build_local_fit_judgment(opportunity: OpportunityFitJudgeCandidate, unavailable_reason: str) -> dict[str, Any]:
    fit = "strong" if opportunity.match.match_score >= 78 else "possible"
    risk_notes = list_from_candidates(
        [*opportunity.match.risks[:2], unavailable_reason],
        fallback=[unavailable_reason],
        max_items=3,
    )

    return {
        "record_ref": opportunity.record_ref,
        "fit": fit,
        "should_show": True,
        "confidence": confidence_from_score(opportunity.match.match_score),
        "reason": local_fit_reason(opportunity.match),
        "risk_notes": risk_notes,
    }


def local_fit_reason(match: OpportunityMatchContext) -> str:
    if match.reasons:
        return str(match.reasons[0])[:240]
    return f"Existing FundRadar scoring rated this as a {round(match.match_score)}% match."


def build_local_analysis(
    *,
    profile: dict[str, Any],
    match: OpportunityMatchContext,
    fit_judgment: OpportunityFitJudgment | None,
    unavailable_reason: str,
) -> dict[str, Any]:
    title = normalize_string(match.title, "this opportunity", max_length=180)
    sponsor = normalize_string(match.sponsor, "", max_length=180)
    score_label = f"{round(match.match_score)}%" if match.match_score else "a low-confidence"
    reason_text = "; ".join(match.reasons[:2])
    summary_parts = [
        f"{title} is a {score_label} match based on the company profile and active benefit record.",
    ]
    if reason_text:
        summary_parts.append(f"Top match signals: {reason_text}.")
    elif sponsor:
        summary_parts.append(f"Confirm the fit directly with {sponsor} before applying.")
    else:
        summary_parts.append("Confirm eligibility against the official program page before applying.")

    missing = missing_profile_fields(profile)
    eligibility_flags = list_from_candidates(
        [
            *match.reasons[:4],
            f"Deadline or intake status: {match.deadline}" if match.deadline else "",
            f"Potential funding estimate: ${match.potential_funding:,.0f}" if match.potential_funding else "",
        ],
        fallback=["Review the official eligibility criteria and eligible expense categories."],
        max_items=5,
    )
    application_steps = list_from_candidates(
        [
            *match.next_actions[:4],
            "Open the official program page and verify the current intake status.",
            "Map the company project budget to eligible expenses before starting the application.",
        ],
        fallback=[
            "Open the official program page and verify the current intake status.",
            "Map the company project budget to eligible expenses before starting the application.",
        ],
        max_items=5,
    )
    risk_notes = list_from_candidates(
        [
            *(fit_judgment.risk_notes[:2] if fit_judgment else []),
            *match.risks[:4],
            unavailable_reason,
        ],
        fallback=[unavailable_reason],
        max_items=5,
    )

    return {
        "fit": fit_judgment.fit if fit_judgment else fit_from_score(match.match_score),
        "should_show": fit_judgment.should_show if fit_judgment else match.match_score >= 45,
        "fit_summary": " ".join(summary_parts)[:520],
        "eligibility_flags": eligibility_flags,
        "missing_company_info": missing,
        "application_steps": application_steps,
        "risk_notes": risk_notes,
        "questions_to_answer": build_local_questions(match),
        "confidence": fit_judgment.confidence if fit_judgment else confidence_from_score(match.match_score),
        "provider": "local-fallback",
    }


def missing_profile_fields(profile: dict[str, Any]) -> list[str]:
    checks = [
        ("legalEntityName", "Legal entity name"),
        ("province", "Province"),
        ("companyType", "Company type"),
        ("employeeRange", "Employee count range"),
        ("industry", "Industry"),
        ("subSector", "Sub-sector"),
        ("fundingNeed", "Funding need"),
        ("keywords", "Keywords or project focus"),
    ]
    missing = [label for key, label in checks if not str(profile.get(key) or "").strip()]
    return missing[:6]


def build_local_questions(match: OpportunityMatchContext) -> list[str]:
    return list_from_candidates(
        [
            "Does the project match the program's eligible activities and expenses?",
            "Can the company satisfy location, sector, and applicant-type rules?",
            "What documents are required before the intake deadline?",
            "Is the estimated funding amount realistic for this program?",
            "Who owns the application and follow-up with the program sponsor?",
        ],
        fallback=["What company facts are needed to verify eligibility?"],
        max_items=5,
    )


def list_from_candidates(candidates: list[str], *, fallback: list[str], max_items: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = re.sub(r"\s+", " ", str(candidate or "").strip())[:180]
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= max_items:
            break
    return output or fallback[:max_items]


def confidence_from_score(score: float) -> str:
    if score >= 72:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def fit_from_score(score: float) -> str:
    if score >= 78:
        return "strong"
    if score >= 45:
        return "possible"
    return "weak"


def build_opportunity_prompt(
    *,
    profile: dict[str, Any],
    opportunity: dict[str, Any],
    match: OpportunityMatchContext,
    fit_judgment: OpportunityFitJudgment | None,
) -> str:
    schema = {
        "fit": "strong | possible | weak",
        "should_show": "boolean",
        "fit_summary": "2 concise sentences explaining the match using only provided evidence",
        "eligibility_flags": ["eligibility signals to verify"],
        "missing_company_info": ["company facts needed before applying"],
        "application_steps": ["practical next steps"],
        "risk_notes": ["risks, gaps, or reasons this may not fit"],
        "questions_to_answer": ["questions the applicant should answer"],
        "confidence": "low | medium | high",
    }
    context = {
        "source": match.source,
        "title": match.title,
        "sponsor": match.sponsor,
        "description": match.description,
        "deadline": match.deadline,
        "status_label": match.status_label,
        "match_score": match.match_score,
        "semantic_score": match.semantic_score,
        "rule_score": match.rule_score,
        "potential_funding": match.potential_funding,
        "reasons": match.reasons,
        "risks": match.risks,
        "next_actions": match.next_actions,
    }
    judgment_context = (
        {
            "fit": fit_judgment.fit,
            "should_show": fit_judgment.should_show,
            "confidence": fit_judgment.confidence,
            "reason": fit_judgment.reason,
            "risk_notes": fit_judgment.risk_notes,
        }
        if fit_judgment
        else None
    )

    return (
        "You are FundRadar's Canadian funding analyst. Explain one active funding opportunity against one company profile.\n"
        "Use only the supplied profile, opportunity record, and match context. Do not invent eligibility, deadlines, funding amounts, "
        "or application requirements. Do not say the company is definitely eligible. If source evidence is weak or missing, put that "
        "in missing_company_info, risk_notes, or questions_to_answer.\n"
        "If an LLM fit-filter judgment is supplied, your fit, should_show, confidence, summary, and risks must respect that judgment. "
        "Do not upgrade a weak/excluded filter judgment in the detailed analysis.\n"
        "Return only valid JSON matching the response shape. Keep every list item short and actionable.\n\n"
        f"Response shape:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"Company profile:\n{compact_json(profile)}\n\n"
        f"Match context:\n{compact_json(context)}\n\n"
        f"LLM fit-filter judgment:\n{compact_json(judgment_context)}\n\n"
        f"Raw active opportunity record:\n{compact_json(opportunity)}"
    )


def parse_gemini_json(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise OpportunityAnalysisUnavailable("Gemini returned no candidates.")

    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    text = ""
    if isinstance(parts, list):
        text = "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))

    if not text.strip():
        raise OpportunityAnalysisUnavailable("Gemini returned an empty response.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = json.loads(extract_json_object(text))

    if not isinstance(parsed, dict):
        raise OpportunityAnalysisUnavailable("Gemini returned JSON in an unexpected shape.")

    return parsed


def normalize_analysis_payload(
    payload: dict[str, Any],
    *,
    match: OpportunityMatchContext | None = None,
    fit_judgment: OpportunityFitJudgment | None = None,
) -> dict[str, Any]:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else payload
    if not isinstance(analysis, dict):
        analysis = {}

    score = match.match_score if match else 50
    fit = fit_judgment.fit if fit_judgment else normalize_fit(analysis.get("fit"), score)
    should_show_raw = analysis.get("should_show")
    if fit_judgment:
        should_show = fit_judgment.should_show
    elif isinstance(should_show_raw, bool):
        should_show = should_show_raw
    else:
        should_show = fit != "weak"
    confidence = fit_judgment.confidence if fit_judgment else normalize_confidence(analysis.get("confidence"))
    fit_summary = normalize_string(
        analysis.get("fit_summary"),
        "Review this opportunity against the company profile and confirm eligibility details on the official program page.",
        max_length=520,
    )

    if fit_judgment:
        filter_summary = (
            f"LLM fit filter rated this as {fit_judgment.fit} "
            f"and {'kept it visible' if fit_judgment.should_show else 'excluded it from default results'} "
            f"because {fit_judgment.reason}"
        )
        fit_summary = normalize_string(f"{filter_summary}. {fit_summary}", filter_summary, max_length=520)

    risk_notes = normalize_string_list(analysis.get("risk_notes"), max_items=6, max_length=180)
    if fit_judgment:
        risk_notes = list_from_candidates(
            [fit_judgment.reason, *fit_judgment.risk_notes, *risk_notes],
            fallback=risk_notes or [fit_judgment.reason],
            max_items=6,
        )

    return {
        "fit": fit,
        "should_show": should_show,
        "fit_summary": fit_summary,
        "eligibility_flags": normalize_string_list(analysis.get("eligibility_flags"), max_items=6, max_length=180),
        "missing_company_info": normalize_string_list(analysis.get("missing_company_info"), max_items=6, max_length=180),
        "application_steps": normalize_string_list(analysis.get("application_steps"), max_items=6, max_length=180),
        "risk_notes": risk_notes,
        "questions_to_answer": normalize_string_list(analysis.get("questions_to_answer"), max_items=6, max_length=180),
        "confidence": confidence,
    }


def normalize_string(value: Any, fallback: str, *, max_length: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return (text or fallback)[:max_length]


def normalize_string_list(value: Any, *, max_items: int, max_length: int) -> list[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = value
    else:
        candidates = []

    output: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        text = re.sub(r"\s+", " ", str(item or "").strip())[:max_length]
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= max_items:
            break

    return output


def normalize_confidence(value: Any) -> str:
    if isinstance(value, (int, float)):
        score = max(0.0, min(1.0, float(value)))
        if score >= 0.72:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"

    normalized = str(value or "").strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    if normalized in {"med", "moderate"}:
        return "medium"
    return "medium"


def compact_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
    return text if len(text) <= MAX_JSON_CONTEXT_CHARS else f"{text[:MAX_JSON_CONTEXT_CHARS]}... [truncated]"


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise OpportunityAnalysisUnavailable("Gemini did not return valid JSON.")
    return text[start : end + 1]


def google_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
