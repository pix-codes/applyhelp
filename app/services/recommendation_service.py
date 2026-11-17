"""Service for generating skill and CV recommendations.

Redacts personal identifiers before sending the payload to the LLM.
"""
import json
from typing import Any, Dict

from app.utils.async_runner import run_async
from app.services.llm.factory import LLMFactory
from app.repositories.settings_repo import SettingsRepository

REDACT_FIELDS = ["name", "email", "profile_url", "phone"]

def _redact(value: Any) -> Any:
    """Recursively replace values with '[REDACTED]'"""
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return "[REDACTED]"

def _redact_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *profile* with personal fields redacted."""
    redacted = profile.copy()
    for field in REDACT_FIELDS:
        if field in redacted:
            redacted[field] = _redact(redacted[field])
    return redacted

async def _call_llm(prompt: str, provider: str | None = None, model: str | None = None) -> str:
    settings_repo = SettingsRepository()
    provider = provider or settings_repo.get("finetuner_llm_provider")
    model = model or settings_repo.get("finetuner_llm_model")
    llm = LLMFactory.create_provider(provider_name=provider, model_name=model)
    response = await llm.chat([{"role": "user", "content": prompt}])
    return getattr(response, "content", str(response))

async def generate_recommendations(profile: Dict[str, Any], market_data: Any) -> Dict[str, Any]:
    """Generate skill and CV recommendations.

    Returns a dict with keys ``skills`` and ``cv``.
    """
    redacted = _redact_profile(profile)
    skill_prompt = (
        f"Based on the following candidate profile (personal info redacted) and current job market trends, "
        f"suggest five concrete skills or technologies the candidate should learn to improve employability. "
        f"Provide a short justification for each.\n\nProfile: {json.dumps(redacted, ensure_ascii=False)}\n\nMarket Data: {json.dumps(market_data, ensure_ascii=False)}"
    )
    cv_prompt = (
        f"Rewrite the candidate's CV summary to better align with the suggested skills and the job market. "
        f"Do not include any personal identifiers. Use a professional tone.\n\nProfile: {json.dumps(redacted, ensure_ascii=False)}\n\nSuggested Skills: (you may reference the output of the skill prompt)"
    )
    skills = await _call_llm(skill_prompt, provider, model)
    cv = await _call_llm(cv_prompt, provider, model)
    return {"skills": skills, "cv": cv}

def get_recommendations(profile: Dict[str, Any], market_data: Any) -> Dict[str, Any]:
    """Sync wrapper used by the UI layer. Executes async workflow via ``run_async``."""
    return run_async(lambda: generate_recommendations(profile, market_data))
