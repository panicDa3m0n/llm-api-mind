from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMProviderError(Exception):
    """Base class for LLM provider failures."""


class LLMConfigurationError(LLMProviderError):
    """Raised when provider configuration is incomplete or invalid."""


class LLMRequestError(LLMProviderError):
    """Raised when the upstream LLM provider request fails."""


class LLMTextResult(BaseModel):
    model: str
    text: str
    usage: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(Protocol):
    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        """Generate text from a single user prompt."""
