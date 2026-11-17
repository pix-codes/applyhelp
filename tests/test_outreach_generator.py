from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models import CandidateProfile, Company, CompanyContact
from app.services.llm.base import LLMResponse
from app.services.outreach.generator import GeneratedOutreach, OutreachGenerator


@pytest.mark.asyncio
async def test_cross_model_review_anti_slop():
    candidate = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        location="Kathmandu, Nepal",
        professional_summary="Backend Engineer with 5 years experience.",
        technical_skills=["Python", "PostgreSQL", "FastAPI"],
    )
    company = Company(name="Acme Corp", normalized_name="acmecorp")
    contact = CompanyContact(name="Alex Smith", role="VP of Engineering", email="alex@acme.com")

    with patch("app.services.outreach.generator.SettingsRepository") as mock_repo_cls, \
         patch("app.services.outreach.generator.LLMFactory.get_configured_providers", return_value=["groq", "mistral"]), \
         patch("app.services.outreach.generator.LLMFactory.create_provider") as mock_create_provider, \
         patch("app.services.outreach.generator.record_llm_usage"):

        mock_repo = MagicMock()
        mock_repo.get.return_value = "groq"
        mock_repo_cls.return_value = mock_repo

        # Generator provider (Groq)
        gen_llm = MagicMock()
        initial_outreach = GeneratedOutreach(
            subject="Excited to connect!",
            body="I hope this email finds you well. I was blown away by Acme Corp.",
            talking_points=["FastAPI expertise"],
        )
        gen_llm.generate_structured = AsyncMock(return_value=(
            initial_outreach,
            LLMResponse(content="", model="llama-3.3-70b-versatile", provider="groq")
        ))

        # Reviewer provider (Mistral)
        rev_llm = MagicMock()
        polished_outreach = GeneratedOutreach(
            subject="Backend engineering at Acme",
            body="Noticed Acme's focus on scalable APIs. I build high-throughput FastAPI systems.",
            talking_points=["FastAPI expertise"],
        )
        rev_llm.generate_structured = AsyncMock(return_value=(
            polished_outreach,
            LLMResponse(content="", model="mistral-large-latest", provider="mistral")
        ))

        def provider_side_effect(provider_name, db=None, **kwargs):
            if provider_name == "groq":
                return gen_llm
            elif provider_name == "mistral":
                return rev_llm
            return gen_llm

        mock_create_provider.side_effect = provider_side_effect

        generator = OutreachGenerator(db=None)
        result = await generator.generate_email(
            candidate=candidate,
            company=company,
            contact=contact,
        )

        assert result.subject == "Backend engineering at Acme"
        assert "blown away" not in result.body
        assert result.reviewed_by == "mistral (mistral-large-latest)"
        assert mock_create_provider.call_count == 2


@pytest.mark.asyncio
async def test_cross_model_review_fallback_on_rate_limit():
    candidate = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        location="Kathmandu, Nepal",
        professional_summary="Backend Engineer with 5 years experience.",
        technical_skills=["Python", "PostgreSQL", "FastAPI"],
    )
    company = Company(name="Acme Corp", normalized_name="acmecorp")
    contact = CompanyContact(name="Alex Smith", role="VP of Engineering", email="alex@acme.com")

    # Both mistral and gemini are configured as candidate reviewers
    with patch("app.services.outreach.generator.SettingsRepository") as mock_repo_cls, \
         patch("app.services.outreach.generator.LLMFactory.get_configured_providers", return_value=["groq", "mistral", "gemini"]), \
         patch("app.services.outreach.generator.LLMFactory.create_provider") as mock_create_provider, \
         patch("app.services.outreach.generator.record_llm_usage"):

        mock_repo = MagicMock()
        mock_repo.get.return_value = "groq"
        mock_repo_cls.return_value = mock_repo

        # Generator (Groq)
        gen_llm = MagicMock()
        initial_outreach = GeneratedOutreach(
            subject="Initial draft",
            body="Initial unpolished body.",
            talking_points=["FastAPI"],
        )
        gen_llm.generate_structured = AsyncMock(return_value=(
            initial_outreach,
            LLMResponse(content="", model="llama-3.3-70b-versatile", provider="groq")
        ))

        # Reviewer 1 (Mistral) raises 429 Rate Limit
        mistral_llm = MagicMock()
        mistral_llm.generate_structured = AsyncMock(side_effect=RuntimeError("429 Rate limit exceeded"))

        # Reviewer 2 (Gemini) succeeds
        gemini_llm = MagicMock()
        polished_outreach = GeneratedOutreach(
            subject="Refined draft by Gemini",
            body="Crisp polished body without slop.",
            talking_points=["FastAPI"],
        )
        gemini_llm.generate_structured = AsyncMock(return_value=(
            polished_outreach,
            LLMResponse(content="", model="gemini-1.5-flash", provider="gemini")
        ))

        def provider_side_effect(provider_name, db=None, **kwargs):
            if provider_name == "groq":
                return gen_llm
            elif provider_name == "mistral":
                return mistral_llm
            elif provider_name == "gemini":
                return gemini_llm
            return gen_llm

        mock_create_provider.side_effect = provider_side_effect

        generator = OutreachGenerator(db=None)
        result = await generator.generate_email(
            candidate=candidate,
            company=company,
            contact=contact,
        )

        # Verified fallback from rate-limited mistral to gemini
        assert result.subject == "Refined draft by Gemini"
        assert result.reviewed_by == "gemini (gemini-1.5-flash)"
