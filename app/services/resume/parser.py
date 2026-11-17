import io
import logging
from typing import List, Optional

import fitz  # PyMuPDF
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.repositories.candidate import CandidateRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.candidate import (
    CandidateExperienceCreate,
    CandidateProfileUpdate,
    CandidateProjectCreate,
)
from app.services.llm.factory import LLMFactory, record_llm_usage
from app.services.llm.prompts import get_prompt

logger = logging.getLogger(__name__)


class ExtractedExperience(BaseModel):
    title: str = Field(description="Job title, e.g. Senior Software Engineer")
    company: str = Field(description="Company or employer name")
    start_date: Optional[str] = Field(default=None, description="Start date (e.g. 'Jan 2021' or '2021')")
    end_date: Optional[str] = Field(default=None, description="End date (e.g. 'Present' or '2023')")
    description: Optional[str] = Field(default=None, description="Bullet points and key responsibilities")
    technologies: List[str] = Field(default_factory=list, description="List of technologies used in this role")


class ExtractedProject(BaseModel):
    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None, description="Project overview and impact")
    url: Optional[str] = Field(default=None, description="Live URL or demo link if mentioned")
    github_url: Optional[str] = Field(default=None, description="GitHub repository link if mentioned")
    technologies: List[str] = Field(default_factory=list, description="Technologies used in this project")


class ExtractedCandidateProfile(BaseModel):
    full_name: str = Field(description="Full name of candidate")
    email: str = Field(description="Email address")
    location: str = Field(default="Nepal", description="Location or country of residence")
    professional_summary: str = Field(description="Concise 2-3 sentence professional summary")
    technical_skills: List[str] = Field(description="List of core programming languages, frameworks, databases, and tools")
    preferred_job_titles: List[str] = Field(description="Inferred appropriate target job titles based on experience")
    github_url: Optional[str] = Field(default=None, description="GitHub profile URL")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    portfolio_url: Optional[str] = Field(default=None, description="Personal portfolio or blog URL")
    experiences: List[ExtractedExperience] = Field(default_factory=list, description="Work history")
    projects: List[ExtractedProject] = Field(default_factory=list, description="Key projects")


class ResumeParserService:
    """
    Extracts text from PDF resume via PyMuPDF and parses structured details using LLM.
    """

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extracts readable text from PDF bytes using PyMuPDF."""
        text_parts = []
        with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n".join(text_parts).strip()

    @staticmethod
    async def parse_and_update_profile(
        pdf_bytes: bytes,
        db: Session,
    ) -> ExtractedCandidateProfile:
        raw_text = ResumeParserService.extract_text_from_pdf(pdf_bytes)
        if not raw_text or len(raw_text) < 50:
            raise ValueError("Could not extract sufficient text from PDF. Ensure it is a text-based PDF.")

        repo = SettingsRepository(db) if db else None
        system_prompt = get_prompt("resume_parser_system", repo=repo)

        user_prompt = f"RESUME TEXT CONTENT:\n{raw_text[:5000]}"

        llm = LLMFactory.create_provider(db=db)
        parsed, raw_resp = await llm.generate_structured(
            prompt=user_prompt,
            schema=ExtractedCandidateProfile,
            system_prompt=system_prompt,
        )
        record_llm_usage(db, raw_resp, purpose="resume_parsing")

        # Save to Candidate Profile repository
        repo = CandidateRepository(db)
        profile = repo.get_or_create_default()

        # Update core profile attributes
        repo.update_profile(
            profile.id,
            CandidateProfileUpdate(
                full_name=parsed.full_name or profile.full_name,
                email=parsed.email or profile.email,
                location=parsed.location or profile.location,
                professional_summary=parsed.professional_summary,
                technical_skills=parsed.technical_skills,
                preferred_job_titles=parsed.preferred_job_titles,
                github_url=parsed.github_url or profile.github_url,
                linkedin_url=parsed.linkedin_url or profile.linkedin_url,
                portfolio_url=parsed.portfolio_url or profile.portfolio_url,
            ),
        )

        # Clear existing experiences/projects to avoid duplication on fresh import
        for exp in list(profile.experiences):
            repo.delete_experience(exp.id)
        for proj in list(profile.projects):
            repo.delete_project(proj.id)

        # Insert extracted experiences
        for exp in parsed.experiences:
            repo.add_experience(
                profile.id,
                CandidateExperienceCreate(
                    title=exp.title,
                    company=exp.company,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    description=exp.description,
                    technologies=exp.technologies,
                ),
            )

        # Insert extracted projects
        for proj in parsed.projects:
            repo.add_project(
                profile.id,
                CandidateProjectCreate(
                    name=proj.name,
                    description=proj.description,
                    url=proj.url,
                    github_url=proj.github_url,
                    technologies=proj.technologies,
                ),
            )

        return parsed
