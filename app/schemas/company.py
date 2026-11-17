from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyContactBase(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    source_evidence_url: str | None = None
    is_verified: bool = False


class CompanyContactCreate(CompanyContactBase):
    pass


class CompanyContactOut(CompanyContactBase):
    id: UUID
    company_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CompanyResearchBase(BaseModel):
    product_summary: str | None = None
    engineering_challenges: str | None = None
    engineering_stack: list[str] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    raw_scraped_snippet: str | None = None


class CompanyResearchCreate(CompanyResearchBase):
    company_id: UUID


class CompanyResearchOut(CompanyResearchBase):
    id: UUID
    company_id: UUID
    last_researched_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CompanyBase(BaseModel):
    name: str
    website_url: str | None = None
    careers_url: str | None = None
    industry: str | None = None
    company_size: str | None = None
    remote_policy: str = "Unknown"
    geographic_eligibility: str = "Unknown"  # Worldwide, Country-specific, Nepal-eligible, Unknown, Excluded
    eligibility_notes: str | None = None
    source_name: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyOut(CompanyBase):
    id: UUID
    normalized_name: str
    created_at: datetime
    updated_at: datetime
    research: CompanyResearchOut | None = None
    contacts: list[CompanyContactOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
