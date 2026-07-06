from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OpenRouterRetrievalError(Exception):
    code: str
    message: str
    status_code: int | None = None
    payload: Any | None = None


class OpenRouterRetrievalClient:
    """Small client for OpenRouter embedding and rerank experiments."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def embed_texts(self, *, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = self._post(
            "/embeddings",
            {
                "model": model,
                "input": texts,
                "encoding_format": "float",
            },
        )
        raw_items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_items, list):
            raise OpenRouterRetrievalError(
                code="openrouter.embeddings.invalid_response",
                message="OpenRouter embedding response did not contain a data list.",
                payload=data,
            )
        vectors: list[list[float]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            vector = _coerce_vector(item.get("embedding"))
            if vector is not None:
                vectors.append(vector)
        if len(vectors) != len(texts):
            raise OpenRouterRetrievalError(
                code="openrouter.embeddings.count_mismatch",
                message=(
                    "OpenRouter returned a different number of embeddings than "
                    "the requested input count."
                ),
                payload={"requested": len(texts), "returned": len(vectors)},
            )
        return vectors

    def rerank(
        self,
        *,
        model: str,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> dict[str, Any]:
        if not documents:
            return {"model": model, "results": [], "usage": {}}
        return self._post(
            "/rerank",
            {
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            },
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise OpenRouterRetrievalError(
                code="openrouter.request_failed",
                message=str(exc),
            ) from exc

        data: Any
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.status_code >= 400:
            raise OpenRouterRetrievalError(
                code="openrouter.error_response",
                message=f"OpenRouter returned HTTP {response.status_code}.",
                status_code=response.status_code,
                payload=data,
            )
        if not isinstance(data, dict):
            raise OpenRouterRetrievalError(
                code="openrouter.invalid_json",
                message="OpenRouter response JSON was not an object.",
                payload=data,
            )
        return data


def _coerce_vector(value: Any) -> list[float] | None:
    if not isinstance(value, list):
        return None
    vector: list[float] = []
    for item in value:
        if not isinstance(item, (int, float)):
            return None
        vector.append(float(item))
    return vector
