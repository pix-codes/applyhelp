from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidateExperienceBase(BaseModel):
    title: str
    company: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class CandidateExperienceCreate(CandidateExperienceBase):
    pass


class CandidateExperienceOut(CandidateExperienceBase):
    id: UUID
    candidate_id: UUID
    model_config = ConfigDict(from_attributes=True)


class CandidateProjectBase(BaseModel):
    name: str
    description: str | None = None
    url: str | None = None
    github_url: str | None = None
    technologies: list[str] = Field(default_factory=list)


class CandidateProjectCreate(CandidateProjectBase):
    pass


class CandidateProjectOut(CandidateProjectBase):
    id: UUID
    candidate_id: UUID
    model_config = ConfigDict(from_attributes=True)


class CandidateProfileBase(BaseModel):
    full_name: str
    email: str
    location: str = "Nepal"
    professional_summary: str | None = None
    technical_skills: list[str] = Field(default_factory=list)
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    preferred_job_titles: list[str] = Field(default_factory=list)
    remote_work_preferences: str = "Remote (Worldwide / Nepal eligible)"
    salary_expectations: str | None = None
    employment_preferences: str = "Full-time, Contract"


class CandidateProfileCreate(CandidateProfileBase):
    pass


class CandidateProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    location: str | None = None
    professional_summary: str | None = None
    technical_skills: list[str] | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    preferred_job_titles: list[str] | None = None
    remote_work_preferences: str | None = None
    salary_expectations: str | None = None
    employment_preferences: str | None = None


class CandidateProfileOut(CandidateProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    experiences: list[CandidateExperienceOut] = Field(default_factory=list)
    projects: list[CandidateProjectOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
