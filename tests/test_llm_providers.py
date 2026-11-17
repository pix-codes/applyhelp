from app.services.llm.providers.gemini_rest import GeminiRestProvider
from app.services.llm.providers.groq_provider import GroqProvider
from app.services.llm.providers.openai_compatible import OpenAICompatibleProvider


def test_provider_initialization():
    groq = GroqProvider(api_key="mock_key", model_name="llama-3.3-70b-versatile")
    assert groq.model_name == "llama-3.3-70b-versatile"

    gemini = GeminiRestProvider(api_key="mock_key", model_name="gemini-1.5-flash")
    assert gemini.base_url == "https://generativelanguage.googleapis.com"

    openai = OpenAICompatibleProvider(api_key="mock_key", model_name="gpt-4o-mini")
    assert openai.model_name == "gpt-4o-mini"

    # Test NVIDIA via LLMFactory
    from app.services.llm.factory import LLMFactory
    nvidia = LLMFactory.create_provider(provider_name="nvidia", model_name="minimaxai/minimax-m3.1-flash")
    assert nvidia.model_name == "minimaxai/minimax-m3.1-flash"
    assert nvidia.base_url == "https://integrate.api.nvidia.com/v1"
