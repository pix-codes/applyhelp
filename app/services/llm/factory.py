import logging

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models import LLMUsage
from app.repositories.settings_repo import SettingsRepository
from app.services.llm.base import BaseLLMProvider, LLMResponse
from app.services.llm.providers.gemini_rest import GeminiRestProvider
from app.services.llm.providers.groq_provider import GroqProvider
from app.services.llm.providers.mistral_provider import MistralProvider
from app.services.llm.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

DEFAULT_MODELS_PER_PROVIDER = {
    "groq": "llama-3.3-70b-versatile",
    "mistral": "mistral-large-latest",
    "gemini": "gemini-1.5-flash",
    "gemini_rest": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "openai_compatible": "gpt-4o-mini",
    "nvidia": "minimaxai/minimax-m3.1-flash",
}


class LLMFactory:
    """
    Builds the selected LLM provider adapter with Cloudflare AI Gateway support.
    Checks DB SettingsRepository first for user-configured UI keys, falling back to environment settings.
    """

    @staticmethod
    def create_provider(
        provider_name: str | None = None,
        model_name: str | None = None,
        use_gateway: bool = False,
        db: Session | None = None,
    ) -> BaseLLMProvider:
        settings = get_settings()
        repo = SettingsRepository(db) if db else None

        gw_url = (
            (repo.get("cloudflare_gateway_url", settings.cloudflare_gateway_url) if repo else settings.cloudflare_gateway_url)
            if use_gateway
            else None
        )

        prov = (
            provider_name
            or (repo.get("default_llm_provider", settings.default_llm_provider) if repo else settings.default_llm_provider)
        ).lower()

        # Get default model for this provider if none specified or if user configured a model for this provider
        saved_model_for_prov = repo.get(f"{prov}_model") if repo else None
        default_model = (
            model_name
            or saved_model_for_prov
            or DEFAULT_MODELS_PER_PROVIDER.get(prov, "gpt-4o-mini")
        )

        if prov == "groq":
            api_key = (repo.get("groq_api_key") if repo else None) or settings.groq_api_key or ""
            base_url = f"{gw_url}/groq" if gw_url else None
            return GroqProvider(api_key=api_key, model_name=default_model, base_url=base_url)

        elif prov == "mistral":
            api_key = (repo.get("mistral_api_key") if repo else None) or settings.mistral_api_key or ""
            base_url = f"{gw_url}/mistral" if gw_url else None
            return MistralProvider(api_key=api_key, model_name=default_model, base_url=base_url)

        elif prov in ["gemini", "gemini_rest"]:
            api_key = (repo.get("gemini_api_key") if repo else None) or settings.gemini_api_key or ""
            base_url = f"{gw_url}/google-ai-studio" if gw_url else None
            return GeminiRestProvider(api_key=api_key, model_name=default_model, gateway_base_url=base_url)

        elif prov in ["openai", "openai_compatible"]:
            api_key = (repo.get("openai_api_key") if repo else None) or settings.openai_api_key or ""
            base_url = (
                f"{gw_url}/openai"
                if gw_url
                else ((repo.get("openai_base_url") if repo else None) or settings.openai_base_url)
            )
            return OpenAICompatibleProvider(api_key=api_key, model_name=default_model, base_url=base_url)

        elif prov == "nvidia":
            api_key = (repo.get("nvidia_api_key") if repo else None) or settings.nvidia_api_key or ""
            base_url = f"{gw_url}/nvidia" if gw_url else "https://integrate.api.nvidia.com/v1"
            return OpenAICompatibleProvider(api_key=api_key, model_name=default_model, base_url=base_url)

        else:
            raise ValueError(f"Unsupported LLM provider: {prov}")

    @staticmethod
    def get_configured_providers(db: Session | None = None) -> list[str]:
        """Returns a list of provider names that have an API key configured (in DB or env settings)."""
        settings = get_settings()
        repo = SettingsRepository(db) if db else None

        providers = []
        # groq
        if (repo.get("groq_api_key") if repo else None) or settings.groq_api_key:
            providers.append("groq")
        # mistral
        if (repo.get("mistral_api_key") if repo else None) or settings.mistral_api_key:
            providers.append("mistral")
        # gemini
        if (repo.get("gemini_api_key") if repo else None) or settings.gemini_api_key:
            providers.append("gemini")
        # openai
        if (repo.get("openai_api_key") if repo else None) or settings.openai_api_key:
            providers.append("openai")
        # nvidia
        if (repo.get("nvidia_api_key") if repo else None) or settings.nvidia_api_key:
            providers.append("nvidia")

        return providers


def record_llm_usage(
    db: Session,
    response: LLMResponse,
    purpose: str = "general",
) -> None:
    """Records token usage into the PostgreSQL llm_usage table."""
    try:
        usage = LLMUsage(
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            purpose=purpose,
        )
        db.add(usage)
        db.commit()
    except Exception as e:
        logger.warning("Failed to record LLM usage: %s", e)
