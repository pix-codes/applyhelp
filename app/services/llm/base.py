from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str
    provider: str


class BaseLLMProvider(ABC):
    """
    Standard interface for all LLM providers (Groq, Mistral, Gemini REST).
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generates plain text response."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[BaseModel, LLMResponse]:
        """Generates structured response validated against a Pydantic schema."""
