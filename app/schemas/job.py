from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobSkillBase(BaseModel):
    skill_name: str
    is_required: bool = True


class JobSkillCreate(JobSkillBase):
    pass


class JobSkillOut(JobSkillBase):
    id: UUID
    job_id: UUID
    model_config = ConfigDict(from_attributes=True)


class JobBase(BaseModel):
    title: str
    canonical_url: str
    application_url: str | None = None
    employment_type: str = "Full-time"
    location_restrictions: str = "Unknown"
    geographic_eligibility: str = "Unknown"
    nepal_eligible: bool = False
    salary_range: str | None = None
    description: str | None = None
    experience_level: str | None = None
    status: str = "Active"


class JobCreate(JobBase):
    company_name: str
    company_website: str | None = None
    skills: list[str] = Field(default_factory=list)


class JobOut(JobBase):
    id: UUID
    company_id: UUID
    normalized_title: str
    match_score: float | None = None
    match_reasons: list[str] = Field(default_factory=list)
    date_discovered: datetime
    last_verified_at: datetime
    skills: list[JobSkillOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
