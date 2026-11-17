from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.llm.base import LLMResponse
from app.services.llm.prompts import optimize_prompt_with_ai


@pytest.mark.asyncio
async def test_optimize_prompt_with_ai():
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=LLMResponse(
        content="Refined and optimized prompt text without slop.",
        model="llama-3.3-70b-versatile",
        provider="groq",
    ))

    with patch("app.services.llm.factory.LLMFactory.create_provider", return_value=mock_llm):
        result = await optimize_prompt_with_ai(
            prompt_key="outreach_system",
            current_prompt="Initial prompt text",
            user_guidance="Make it sharper and concise",
            db=None,
        )

        assert result == "Refined and optimized prompt text without slop."
        assert mock_llm.generate.call_count == 1


@pytest.mark.asyncio
async def test_optimize_prompt_with_custom_finetuner_provider():
    mock_db = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=LLMResponse(
        content="Refined by NVIDIA Minimax.",
        model="minimaxai/minimax-m3.1-flash",
        provider="nvidia",
    ))

    with patch("app.services.llm.factory.LLMFactory.create_provider", return_value=mock_llm) as mock_create:
        result = await optimize_prompt_with_ai(
            prompt_key="outreach_system",
            current_prompt="Initial prompt text",
            user_guidance="Make it sharper",
            provider_name="nvidia",
            model_name="minimaxai/minimax-m3.1-flash",
            db=mock_db,
        )

        assert result == "Refined by NVIDIA Minimax."
        mock_create.assert_called_once_with(
            provider_name="nvidia",
            model_name="minimaxai/minimax-m3.1-flash",
            db=mock_db,
        )
