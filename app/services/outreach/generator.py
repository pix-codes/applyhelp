import logging

from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.models import CandidateProfile, Company, CompanyContact, Job
from app.repositories.settings_repo import SettingsRepository
from app.services.llm.factory import LLMFactory, record_llm_usage
from app.services.llm.prompts import get_prompt
from app.services.outreach.templates import TEMPLATES

logger = logging.getLogger(__name__)


class GeneratedOutreach(BaseModel):
    subject: str = Field(description="Compelling, natural email subject line without clickbait")
    body: str = Field(description="Personalized cold email message body")
    talking_points: list[str] = Field(description="Key 2-3 genuine talking points used from the profile and research")
    reviewed_by: str | None = Field(default=None, description="The reviewer model/provider that vetted the draft")


class OutreachGenerator:
    """
    Generates tailored, concise outreach emails strictly grounded in the candidate's
    actual experience and verified company facts.
    Includes a cross-model review step to eliminate AI slop, corporate cliches, and hollow buzzwords.
    """

    ANTI_SLOP_REVIEW_PROMPT = (
        "You are a rigorous, no-nonsense executive editor and cold email specialist. "
        "Your task is to review and refine a drafted cold email written for a software engineer to eliminate 'AI slop' "
        "and make it sound like it was written by an authentic human professional.\n\n"
        "RULES FOR REMOVING AI SLOP:\n"
        "1. ELIMINATE all corporate cliches, sycophancy, and filler phrases, such as:\n"
        "   - 'I hope this email finds you well'\n"
        "   - 'I was blown away by / deeply impressed by / intrigued by'\n"
        "   - 'delve into / harness / leverage / testament to / beacon / spearheaded'\n"
        "   - 'seamlessly / dynamic synergy / resonate with'\n"
        "   - 'In today's fast-paced digital world'\n"
        "   - 'I am writing to express my eager interest in'\n"
        "2. GROUNDING & HONESTY: Do NOT invent skills, metrics, accomplishments, or claims not present in the draft/candidate background.\n"
        "3. TONE: Pragmatic, direct, peer-to-peer, and humble yet confident. Speak like a senior builder, not a marketing robot or ChatGPT.\n"
        "4. BREVITY: Keep the body under 140 words. Get directly to the point in the first 2 sentences.\n"
        "5. SPECIFICITY: Preserve specific concrete facts (tech stack, candidate's actual projects, Nepal location/timezone if mentioned) "
        "and cut any vague hand-waving.\n"
        "6. CALL TO ACTION: A light, low-friction, non-pushy closing question (e.g., 'Open to a brief chat next week if you are exploring support on this?')."
    )

    def __init__(self, db):
        self.db = db

    def _select_reviewer_candidates(self, generator_provider: str) -> list[str]:
        """
        Returns a list of configured providers distinct from the generator provider,
        to be tried sequentially as anti-slop reviewers.
        """
        configured = LLMFactory.get_configured_providers(db=self.db)
        return [p for p in configured if p.lower() != generator_provider.lower()]

    async def generate_email(
        self,
        candidate: CandidateProfile,
        company: Company,
        template_type: str = "General Introduction",
        job: Job | None = None,
        contact: CompanyContact | None = None,
    ) -> GeneratedOutreach:
        tmpl_config = TEMPLATES.get(template_type, TEMPLATES["General Introduction"])

        # Compile candidate background
        experiences_summary = "\n".join([
            f"- {e.title} at {e.company}: {e.description} (Tech: {', '.join(e.technologies or [])})"
            for e in (candidate.experiences or [])[:3]
        ])
        projects_summary = "\n".join([
            f"- {p.name}: {p.description} (Tech: {', '.join(p.technologies or [])}, URL: {p.url or p.github_url or 'N/A'})"
            for p in (candidate.projects or [])[:3]
        ])

        # Compile company context
        research = company.research
        product_summary = research.product_summary if research else "SaaS and engineering platform."
        eng_challenges = research.engineering_challenges if research else "Building scalable systems."
        eng_stack = ", ".join(research.engineering_stack) if research and research.engineering_stack else "Modern web stack"

        contact_name = contact.name if contact else (f"{company.name} Engineering Team")
        contact_role = contact.role if contact else "Hiring Team"

        job_context = ""
        if job:
            job_context = f"\nSpecific Open Vacancy: {job.title}\nJob Description Excerpt: {(job.description or '')[:500]}\n"

        repo = SettingsRepository(self.db) if self.db else None
        base_outreach_prompt = get_prompt("outreach_system", repo=repo)
        system_prompt = base_outreach_prompt.replace("{tone_instruction}", tmpl_config.get("tone_instruction", "Genuine and professional"))

        user_prompt = (
            f"RECIPIENT:\nName: {contact_name}\nRole: {contact_role}\nCompany: {company.name}\n\n"
            f"COMPANY RESEARCH:\nProduct: {product_summary}\nEngineering Focus: {eng_challenges}\nKnown Stack: {eng_stack}\n\n"
            f"{job_context}\n"
            f"CANDIDATE PROFILE:\n"
            f"Name: {candidate.full_name}\n"
            f"Summary: {candidate.professional_summary}\n"
            f"Skills: {', '.join(candidate.technical_skills or [])}\n"
            f"Experience:\n{experiences_summary or 'Experienced software engineer'}\n"
            f"Featured Projects:\n{projects_summary or 'Custom backend & infrastructure projects'}\n"
            f"Location: {candidate.location}\n"
            f"Remote Preference: {candidate.remote_work_preferences}\n"
        )

        # 1. Generator Model Step
        settings = get_settings()
        repo = SettingsRepository(self.db) if self.db else None
        gen_provider_name = (
            repo.get("default_llm_provider", settings.default_llm_provider) if repo else settings.default_llm_provider
        ) or "groq"

        llm = LLMFactory.create_provider(provider_name=gen_provider_name, db=self.db)
        res, raw_resp = await llm.generate_structured(
            prompt=user_prompt,
            schema=GeneratedOutreach,
            system_prompt=system_prompt,
        )
        record_llm_usage(self.db, raw_resp, purpose="email_generation")

        # 2. Cross-Model Review Step to Prevent AI Slop
        reviewer_candidates = self._select_reviewer_candidates(gen_provider_name)
        review_errors = []

        for reviewer_provider_name in reviewer_candidates:
            try:
                logger.info(
                    "Draft generated by provider '%s'. Initiating anti-slop review using provider '%s'...",
                    gen_provider_name,
                    reviewer_provider_name,
                )
                reviewer_llm = LLMFactory.create_provider(provider_name=reviewer_provider_name, db=self.db)

                review_user_prompt = (
                    f"ORIGINAL DRAFT SUBJECT:\n{res.subject}\n\n"
                    f"ORIGINAL DRAFT BODY:\n{res.body}\n\n"
                    f"RECIPIENT & COMPANY:\nRecipient: {contact_name} ({contact_role}) at {company.name}\n"
                    f"Company Product: {product_summary}\n"
                    f"Engineering Focus: {eng_challenges}\n\n"
                    f"CANDIDATE PROFILE:\nName: {candidate.full_name}\nLocation: {candidate.location}\n"
                    f"Key Skills: {', '.join(candidate.technical_skills or [])}\n\n"
                    "INSTRUCTIONS:\n"
                    "Critique and polish this draft to remove any AI fluff, overused tropes, buzzwords, or robotic cadence. "
                    "Return the final perfected subject line, body text, and preserved talking points."
                )

                review_system_prompt = get_prompt("outreach_anti_slop_review", repo=repo)
                reviewed_res, review_raw_resp = await reviewer_llm.generate_structured(
                    prompt=review_user_prompt,
                    schema=GeneratedOutreach,
                    system_prompt=review_system_prompt,
                )
                record_llm_usage(self.db, review_raw_resp, purpose="email_review")
                reviewed_res.reviewed_by = f"{reviewer_provider_name} ({review_raw_resp.model})"
                return reviewed_res
            except Exception as e:
                logger.warning(
                    "Cross-model review by provider '%s' failed: %s; trying next reviewer...",
                    reviewer_provider_name,
                    e,
                )
                review_errors.append(f"{reviewer_provider_name}: {e}")

        # If all candidates failed or none configured
        if review_errors:
            res.reviewed_by = f"Unreviewed (Review failed - {'; '.join(review_errors)})"
        else:
            res.reviewed_by = None
        return res
