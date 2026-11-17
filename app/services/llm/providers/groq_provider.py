import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.services.llm.base import BaseLLMProvider, LLMResponse


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile", base_url: str | None = None):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    def _get_client(self, temperature: float, max_tokens: int = 4000) -> ChatGroq:
        kwargs = {
            "api_key": self.api_key,
            "model_name": self.model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return ChatGroq(**kwargs)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> LLMResponse:
        client = self._get_client(temperature=temperature, max_tokens=max_tokens)
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        res = await client.ainvoke(messages)
        usage = getattr(res, "usage_metadata", {}) or {}

        return LLMResponse(
            content=res.content,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=self.model_name,
            provider="groq",
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> tuple[BaseModel, LLMResponse]:
        client = self._get_client(temperature=temperature, max_tokens=max_tokens)
        structured_llm = client.with_structured_output(schema)

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        result = await structured_llm.ainvoke(messages)
        # Wrap into standard response
        response_obj = LLMResponse(
            content=json.dumps(result.model_dump() if hasattr(result, "model_dump") else {}),
            model=self.model_name,
            provider="groq",
        )
        return result, response_obj
