from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from publicus_backend.schemas.profile_copilot import ProfileCopilotAnswer


ACTIVITY_KEYS = ["research", "hiring", "equipment", "export", "facilities", "sustainability"]
COMPANY_TYPES = ["for-profit", "nonprofit", "academic", "public-sector"]
EMPLOYEE_RANGES = ["1-10", "11-50", "51-200", "200+"]
PROVINCES = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}
INDUSTRY_OPTIONS = {
    "tech": ("Technology & Software", ["technology", "software", "digital", "data", "ai", "saas"]),
    "mfg": ("Manufacturing", ["manufacturing", "equipment", "production", "factory"]),
    "agri": ("Agriculture", ["agriculture", "agri-food", "farm", "food"]),
    "health": ("Healthcare & Life Sciences", ["health", "life sciences", "medical", "biotech"]),
    "clean": ("CleanTech", ["clean technology", "cleantech", "sustainability", "climate", "energy"]),
}
SUB_SECTOR_OPTIONS = {
    "ai": ("Artificial Intelligence (AI)", ["ai", "artificial intelligence", "machine learning"]),
    "saas": ("B2B SaaS", ["saas", "software", "cloud"]),
    "cybersecurity": ("Cybersecurity", ["cybersecurity", "cyber security", "security", "privacy"]),
    "data": ("Data & Analytics", ["data", "analytics", "business intelligence", "reporting"]),
    "fintech": ("FinTech", ["fintech", "financial technology", "payments", "banking"]),
    "healthtech": ("HealthTech / MedTech", ["healthtech", "medtech", "medical device", "digital health"]),
    "biotech": ("Biotechnology", ["biotechnology", "biotech", "life sciences", "biomanufacturing"]),
    "advanced-mfg": ("Advanced Manufacturing", ["advanced manufacturing", "manufacturing", "automation", "production"]),
    "robotics": ("Robotics & Automation", ["robotics", "robot", "automation", "industrial automation"]),
    "hardware-iot": ("Hardware / IoT", ["hardware", "iot", "internet of things", "connected device"]),
    "agtech": ("AgTech / FoodTech", ["agtech", "foodtech", "agriculture technology", "food processing"]),
    "clean": ("CleanTech", ["clean technology", "energy", "sustainability"]),
    "clean-energy": ("Clean Energy", ["clean energy", "renewable energy", "solar", "wind"]),
    "ev": ("Electric Vehicles & Batteries", ["electric vehicle", "ev", "battery", "charging"]),
    "circular": ("Circular Economy", ["circular economy", "recycling", "waste reduction", "reuse"]),
    "construction-tech": ("Construction Tech", ["construction technology", "proptech", "building technology", "retrofit"]),
    "aerospace": ("Aerospace", ["aerospace", "aviation", "aircraft", "space"]),
    "ocean": ("Ocean / Marine Tech", ["ocean technology", "marine", "aquaculture", "blue economy"]),
    "supply-chain": ("Supply Chain & Logistics", ["supply chain", "logistics", "transportation", "distribution"]),
    "digital-media": ("Digital Media & Gaming", ["digital media", "gaming", "interactive media", "content"]),
    "edtech": ("Education Technology", ["edtech", "education technology", "learning", "training"]),
    "social-impact": ("Social Impact", ["social impact", "community", "inclusive", "nonprofit"]),
    "accessibility": ("Accessibility Tech", ["accessibility", "accessible", "disability"]),
    "export": ("Export Growth", ["export", "international", "market"]),
}


class ProfileCopilotUnavailable(RuntimeError):
    pass


def extract_company_profile(
    *,
    answers: list[ProfileCopilotAnswer],
    current_profile: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    api_key = google_api_key()
    if not api_key:
        raise ProfileCopilotUnavailable("GEMINI_API_KEY is not configured.")

    baseline = normalize_profile(current_profile)
    payload = call_gemini_profile_extraction(
        prompt=build_profile_prompt(answers, baseline),
        api_key=api_key,
        timeout=timeout,
    )
    parsed = parse_gemini_json(payload)
    extracted = parsed.get("profile") if isinstance(parsed.get("profile"), dict) else parsed
    profile = normalize_profile(extracted if isinstance(extracted, dict) else {}, baseline)

    return {
        "profile": profile,
        "confidence": normalize_confidence(parsed.get("confidence")),
        "notes": normalize_notes(parsed.get("notes")),
        "provider": "google",
    }


def call_gemini_profile_extraction(*, prompt: str, api_key: str, timeout: float) -> dict[str, Any]:
    model = os.getenv("PUBLICUS_GEMINI_GENERATION_MODEL", "gemini-2.0-flash")
    model_path = model if model.startswith("models/") else f"models/{model}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
    request = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
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
                raise ProfileCopilotUnavailable(
                    "Gemini quota or rate limit was reached. Try again later or configure a generation model with available quota."
                ) from exc
            if exc.response.status_code in {401, 403}:
                raise ProfileCopilotUnavailable("Gemini rejected the configured API key or project permissions.") from exc
            raise
        return response.json()


def build_profile_prompt(answers: list[ProfileCopilotAnswer], current_profile: dict[str, Any]) -> str:
    qa_text = "\n".join(f"- {item.question}\n  Answer: {item.answer}" for item in answers)
    schema = {
        "profile": {
            "legalEntityName": "string",
            "doingBusinessAs": "string",
            "incorporationDate": "YYYY-MM-DD or empty string",
            "website": "https URL or empty string",
            "province": list(PROVINCES),
            "city": "string",
            "companyType": COMPANY_TYPES,
            "employeeRange": EMPLOYEE_RANGES,
            "industry": list(INDUSTRY_OPTIONS),
            "subSector": list(SUB_SECTOR_OPTIONS),
            "keywords": "comma-separated string",
            "fundingNeed": "numeric string without currency symbols",
            "activities": {key: "boolean" for key in ACTIVITY_KEYS},
        },
        "confidence": {"fieldName": 0.0},
        "notes": ["short assumption notes"],
    }

    return (
        "You convert plain-language company intake answers into FundRadar's company profile JSON.\n"
        "Return only valid JSON. Use only the enum values listed in the schema. "
        "If a field is unknown, keep the current profile value or use an empty string. "
        "Map funding goals to activities. Keep keywords concise and comma separated.\n\n"
        f"Current profile JSON:\n{json.dumps(current_profile, ensure_ascii=False)}\n\n"
        f"Allowed response shape:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"User answers:\n{qa_text}"
    )


def parse_gemini_json(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ProfileCopilotUnavailable("Gemini returned no candidates.")

    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    text = ""
    if isinstance(parts, list):
        text = "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))

    if not text.strip():
        raise ProfileCopilotUnavailable("Gemini returned an empty response.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = json.loads(extract_json_object(text))

    if not isinstance(parsed, dict):
        raise ProfileCopilotUnavailable("Gemini returned JSON in an unexpected shape.")

    return parsed


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ProfileCopilotUnavailable("Gemini did not return valid JSON.")
    return text[start : end + 1]


def normalize_profile(value: dict[str, Any], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = fallback or {}
    profile = {
        "legalEntityName": read_string(value, "legalEntityName", fallback, 240),
        "doingBusinessAs": read_string(value, "doingBusinessAs", fallback, 240),
        "incorporationDate": normalize_date(value.get("incorporationDate"), fallback.get("incorporationDate")),
        "website": normalize_url(value.get("website"), fallback.get("website")),
        "province": normalize_province(value.get("province"), fallback.get("province")),
        "city": read_string(value, "city", fallback, 120),
        "companyType": normalize_company_type(value.get("companyType"), fallback.get("companyType")),
        "employeeRange": normalize_employee_range(value.get("employeeRange"), fallback.get("employeeRange")),
        "industry": normalize_option(value.get("industry"), INDUSTRY_OPTIONS, fallback.get("industry")),
        "subSector": normalize_option(value.get("subSector"), SUB_SECTOR_OPTIONS, fallback.get("subSector")),
        "keywords": read_string(value, "keywords", fallback, 2000),
        "fundingNeed": normalize_money(value.get("fundingNeed"), fallback.get("fundingNeed")),
        "activities": normalize_activities(value.get("activities"), fallback.get("activities")),
    }
    return profile


def read_string(value: dict[str, Any], key: str, fallback: dict[str, Any], max_length: int) -> str:
    raw = value.get(key)
    if raw is None or str(raw).strip() == "":
        raw = fallback.get(key, "")
    return str(raw).strip()[:max_length] if raw is not None else ""


def normalize_date(value: Any, fallback: Any) -> str:
    candidate = str(value or fallback or "").strip()[:10]
    return candidate if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate) else ""


def normalize_url(value: Any, fallback: Any) -> str:
    candidate = str(value or fallback or "").strip()
    if not candidate:
        return ""
    if not re.match(r"^https?://", candidate, flags=re.I) and "." in candidate:
        candidate = f"https://{candidate}"
    return candidate[:2048] if re.match(r"^https?://", candidate, flags=re.I) else ""


def normalize_province(value: Any, fallback: Any) -> str:
    candidate = str(value or fallback or "").strip()
    if not candidate:
        return ""
    upper = candidate.upper()
    if upper in PROVINCES:
        return upper
    normalized = normalize_text(candidate)
    for code, label in PROVINCES.items():
        if normalize_text(label) == normalized:
            return code
    return ""


def normalize_company_type(value: Any, fallback: Any) -> str:
    candidate = normalize_text(str(value or fallback or ""))
    aliases = {
        "business": "for-profit",
        "company": "for-profit",
        "corporation": "for-profit",
        "startup": "for-profit",
        "for profit": "for-profit",
        "non profit": "nonprofit",
        "nonprofit": "nonprofit",
        "charity": "nonprofit",
        "university": "academic",
        "college": "academic",
        "academic": "academic",
        "municipality": "public-sector",
        "government": "public-sector",
        "public sector": "public-sector",
    }
    if str(value or fallback or "") in COMPANY_TYPES:
        return str(value or fallback or "")
    return aliases.get(candidate, "for-profit")


def normalize_employee_range(value: Any, fallback: Any) -> str:
    raw = str(value or fallback or "").strip()
    if raw in EMPLOYEE_RANGES:
        return raw
    numbers = [int(item) for item in re.findall(r"\d+", raw)]
    if numbers:
        count = max(numbers)
        if count <= 10:
            return "1-10"
        if count <= 50:
            return "11-50"
        if count <= 200:
            return "51-200"
        return "200+"
    return "11-50"


def normalize_option(value: Any, options: dict[str, tuple[str, list[str]]], fallback: Any) -> str:
    raw = str(value or fallback or "").strip()
    if raw in options:
        return raw
    normalized = normalize_text(raw)
    for key, (label, terms) in options.items():
        choices = [key, label, *terms]
        if any(normalize_text(choice) == normalized or normalize_text(choice) in normalized for choice in choices):
            return key
    return ""


def normalize_money(value: Any, fallback: Any) -> str:
    raw = str(value or fallback or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    multiplier = 1
    if re.search(r"\d\s*k\b|thousand", lower):
        multiplier = 1_000
    elif re.search(r"\d\s*m\b|million", lower):
        multiplier = 1_000_000

    match = re.search(r"\d+(?:\.\d+)?", raw.replace(",", ""))
    if not match:
        return ""
    amount = float(match.group(0)) * multiplier
    return str(int(round(amount))) if amount > 0 else ""


def normalize_activities(value: Any, fallback: Any) -> dict[str, bool]:
    source = value if isinstance(value, dict) else fallback if isinstance(fallback, dict) else {}
    return {key: source.get(key) is True for key in ACTIVITY_KEYS}


def normalize_confidence(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    output = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            continue
        try:
            output[key] = max(0.0, min(1.0, float(raw)))
        except (TypeError, ValueError):
            continue
    return output


def normalize_notes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:240] for item in value if str(item).strip()][:5]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("-", " "))


def google_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
