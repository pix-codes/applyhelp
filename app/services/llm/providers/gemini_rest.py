import json
import logging

import httpx
from pydantic import BaseModel

from app.services.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiRestProvider(BaseLLMProvider):
    """
    Direct HTTP REST client for Google Gemini API.
    Does NOT use google-generativeai SDK.
    Supports optional Cloudflare AI Gateway URL rewriting.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash",
        gateway_base_url: str | None = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        # If gateway url provided: e.g. https://gateway.ai.cloudflare.com/v1/{account}/{gateway}/google-ai-studio
        self.base_url = (
            gateway_base_url.rstrip("/")
            if gateway_base_url
            else "https://generativelanguage.googleapis.com"
        )

    def _get_endpoint(self) -> str:
        return f"{self.base_url}/v1beta/models/{self.model_name}:generateContent"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> LLMResponse:
        endpoint = self._get_endpoint()
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Instructions:\n{system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will strictly follow these instructions."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("Gemini REST API error %s: %s", resp.status_code, resp.text)
                raise RuntimeError(f"Gemini REST Error {resp.status_code}: {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            text_content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text_content = parts[0].get("text", "")

            usage = data.get("usageMetadata", {})
            return LLMResponse(
                content=text_content,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
                model=self.model_name,
                provider="gemini_rest",
            )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[BaseModel, LLMResponse]:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"\n\nYou MUST return valid JSON adhering strictly to the following JSON Schema:\n{schema_json}\n"
            "Do NOT wrap the JSON in markdown code fences or backticks. Return raw JSON only."
        )

        full_prompt = prompt + instruction
        resp = await self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        # Parse output
        clean_text = resp.content.strip()
        clean_text = clean_text.removeprefix("```json")
        clean_text = clean_text.removeprefix("```")
        clean_text = clean_text.removesuffix("```")
        clean_text = clean_text.strip()

        parsed_data = schema.model_validate_json(clean_text)
        return parsed_data, resp
