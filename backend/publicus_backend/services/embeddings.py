from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any

import httpx


DEFAULT_EMBEDDING_DIMENSIONS = 1536
DEFAULT_EMBEDDING_PROVIDER = "google"
DEFAULT_GOOGLE_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_GOOGLE_EMBEDDING_BATCH_SIZE = 100
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9&.+#-]*", re.IGNORECASE)
MAX_EMBEDDING_TEXT_LENGTH = 8000

DOMAIN_EXPANSIONS = {
    "ai": ["artificial intelligence", "machine learning", "automation", "data"],
    "artificial": ["ai", "machine learning"],
    "accessibility": ["assistive technology", "inclusive design", "disability"],
    "agriculture": ["agri food", "farm", "food production"],
    "cleantech": ["clean technology", "climate", "energy", "emissions"],
    "digital": ["software", "technology", "online", "data"],
    "export": ["international", "market expansion", "trade"],
    "hiring": ["employment", "jobs", "workforce", "training"],
    "manufacturing": ["production", "equipment", "machinery"],
    "research": ["development", "innovation", "pilot", "r&d"],
    "sustainability": ["climate", "green", "energy", "emissions"],
    "technology": ["software", "digital", "data", "innovation"],
}


def embedding_dimensions() -> int:
    configured = os.getenv("PUBLICUS_EMBEDDING_DIMENSIONS")
    if not configured:
        return DEFAULT_EMBEDDING_DIMENSIONS

    try:
        parsed = int(configured)
    except ValueError:
        return DEFAULT_EMBEDDING_DIMENSIONS

    return parsed if parsed > 0 else DEFAULT_EMBEDDING_DIMENSIONS


def embed_texts(texts: list[str], timeout: float = 30.0) -> tuple[list[list[float]], str]:
    provider = os.getenv("PUBLICUS_EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER).strip().lower()
    google_api_key = google_embedding_api_key(provider)
    openai_api_key = openai_embedding_api_key(provider)

    if provider in {"auto", "google", "gemini"} and google_api_key:
        try:
            return embed_texts_google(texts, api_key=google_api_key, timeout=timeout), "google"
        except Exception:
            if provider in {"google", "gemini"}:
                raise

    if provider in {"auto", "openai"} and openai_api_key:
        try:
            return embed_texts_openai(texts, api_key=openai_api_key, timeout=timeout), "openai"
        except Exception:
            if provider == "openai":
                raise

    return [local_embedding(text, embedding_dimensions()) for text in texts], "local-hash"


def google_embedding_api_key(provider: str) -> str | None:
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
    )
    if api_key:
        return api_key

    if provider in {"google", "gemini"}:
        return os.getenv("EMBEDDING_API_KEY")

    return None


def openai_embedding_api_key(provider: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    if provider == "openai":
        return os.getenv("EMBEDDING_API_KEY")

    return None


def embed_texts_google(texts: list[str], *, api_key: str, timeout: float) -> list[list[float]]:
    model = os.getenv("PUBLICUS_GOOGLE_EMBEDDING_MODEL", DEFAULT_GOOGLE_EMBEDDING_MODEL)
    model_path = google_model_path(model)
    dimensions = embedding_dimensions()
    task_type = os.getenv("PUBLICUS_GOOGLE_EMBEDDING_TASK_TYPE", "SEMANTIC_SIMILARITY")
    results: list[list[float]] = []

    for chunk in chunk_texts(texts, google_embedding_batch_size()):
        results.extend(
            embed_texts_google_batch(
                chunk,
                api_key=api_key,
                model_path=model_path,
                dimensions=dimensions,
                task_type=task_type,
                timeout=timeout,
            )
        )

    return results


def embed_texts_google_batch(
    texts: list[str],
    *,
    api_key: str,
    model_path: str,
    dimensions: int,
    task_type: str,
    timeout: float,
) -> list[list[float]]:
    payload: dict[str, Any] = {
        "requests": [
            {
                "model": model_path,
                "content": {"parts": [{"text": truncate_text(text)}]},
                "task_type": task_type,
                "output_dimensionality": dimensions,
            }
            for text in texts
        ]
    }

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        response = client.post(
            f"https://generativelanguage.googleapis.com/v1beta/{model_path}:batchEmbedContents",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            json=payload,
        )
        response.raise_for_status()

    embeddings = response.json().get("embeddings", [])
    if len(embeddings) != len(texts):
        raise RuntimeError("Embedding provider returned an unexpected response.")

    values = [item.get("values") for item in embeddings]
    if not all(isinstance(item, list) for item in values):
        raise RuntimeError("Embedding provider returned an unexpected response.")

    return [[float(value) for value in item] for item in values]


def google_embedding_batch_size() -> int:
    configured = os.getenv("PUBLICUS_GOOGLE_EMBEDDING_BATCH_SIZE")
    if not configured:
        return DEFAULT_GOOGLE_EMBEDDING_BATCH_SIZE

    try:
        parsed = int(configured)
    except ValueError:
        return DEFAULT_GOOGLE_EMBEDDING_BATCH_SIZE

    return max(1, min(500, parsed))


def chunk_texts(texts: list[str], size: int) -> list[list[str]]:
    return [texts[index : index + size] for index in range(0, len(texts), size)]


def google_model_path(model: str) -> str:
    normalized = model.strip() or DEFAULT_GOOGLE_EMBEDDING_MODEL
    return normalized if normalized.startswith("models/") else f"models/{normalized}"


def embed_texts_openai(texts: list[str], *, api_key: str, timeout: float) -> list[list[float]]:
    model = os.getenv("PUBLICUS_OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL)
    dimensions = embedding_dimensions()
    payload: dict[str, Any] = {
        "model": model,
        "input": [truncate_text(text) for text in texts],
        "dimensions": dimensions,
    }

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        response = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    data = response.json().get("data", [])
    indexed = sorted(data, key=lambda item: int(item.get("index", 0)))
    embeddings = [item.get("embedding") for item in indexed]
    if len(embeddings) != len(texts) or not all(isinstance(item, list) for item in embeddings):
        raise RuntimeError("Embedding provider returned an unexpected response.")

    return [[float(value) for value in item] for item in embeddings]


def local_embedding(text: str, dimensions: int) -> list[float]:
    tokens = tokenize(expand_domain_terms(text))
    vector = [0.0] * dimensions

    for token in tokens:
        add_feature(vector, f"tok:{token}", 1.0)

    for left, right in zip(tokens, tokens[1:]):
        add_feature(vector, f"bigram:{left} {right}", 0.65)

    normalized_text = " ".join(tokens)
    for size in (3, 4, 5):
        for index in range(max(0, len(normalized_text) - size + 1)):
            feature = normalized_text[index : index + size]
            if " " not in feature:
                add_feature(vector, f"char:{feature}", 0.2)

    return normalize_vector(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    return sum(a * b for a, b in zip(left, right))


def vector_literal(vector: list[float]) -> str:
    return f"[{','.join(f'{value:.8f}' for value in vector)}]"


def truncate_text(text: str) -> str:
    return text[:MAX_EMBEDDING_TEXT_LENGTH]


def expand_domain_terms(text: str) -> str:
    normalized = text.lower()
    expansions: list[str] = []

    for term, related_terms in DOMAIN_EXPANSIONS.items():
        if term in normalized:
            expansions.extend(related_terms)

    return " ".join([text, *expansions])


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in EMBEDDING_TOKEN_RE.finditer(truncate_text(text))]


def add_feature(vector: list[float], feature: str, weight: float) -> None:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest[:4], "big") % len(vector)
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    vector[index] += sign * weight


def normalize_vector(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]
