import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid():
    return uuid.uuid4()


# ----------------------------------------------------
# Candidate Models
# ----------------------------------------------------
class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False, default="Nepal")
    professional_summary = Column(Text, nullable=True)
    technical_skills = Column(JSON, default=list, nullable=False)  # list of strings
    github_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    preferred_job_titles = Column(JSON, default=list, nullable=False)
    remote_work_preferences = Column(String(255), default="Remote (Worldwide / Nepal eligible)")
    salary_expectations = Column(String(255), nullable=True)
    employment_preferences = Column(String(255), default="Full-time, Contract")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    experiences = relationship("CandidateExperience", back_populates="candidate", cascade="all, delete-orphan")
    projects = relationship("CandidateProject", back_populates="candidate", cascade="all, delete-orphan")


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    is_current = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    technologies = Column(JSON, default=list)

    candidate = relationship("CandidateProfile", back_populates="experiences")


class CandidateProject(Base):
    __tablename__ = "candidate_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    technologies = Column(JSON, default=list)

    candidate = relationship("CandidateProfile", back_populates="projects")


# ----------------------------------------------------
# Company & Research Models
# ----------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, unique=True, index=True)
    website_url = Column(String(500), nullable=True)
    careers_url = Column(String(500), nullable=True)
    industry = Column(String(255), nullable=True)
    company_size = Column(String(100), nullable=True)
    remote_policy = Column(String(100), default="Unknown")  # Remote-first, Hybrid, etc.
    geographic_eligibility = Column(String(100), default="Unknown", nullable=False)  # Worldwide, Country-specific, Nepal-eligible, Unknown, Excluded
    eligibility_notes = Column(Text, nullable=True)
    source_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    research = relationship("CompanyResearch", back_populates="company", uselist=False, cascade="all, delete-orphan")
    contacts = relationship("CompanyContact", back_populates="company", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")


class CompanyResearch(Base):
    __tablename__ = "company_research"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), unique=True, nullable=False)
    product_summary = Column(Text, nullable=True)
    engineering_challenges = Column(Text, nullable=True)
    engineering_stack = Column(JSON, default=list)  # verified tech stack
    evidence_urls = Column(JSON, default=list)
    raw_scraped_snippet = Column(Text, nullable=True)
    last_researched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="research")


class CompanyContact(Base):
    __tablename__ = "company_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)  # Founder, Engineering Manager, Recruiter
    email = Column(String(255), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    source_evidence_url = Column(String(500), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="contacts")


# ----------------------------------------------------
# Job Models
# ----------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    normalized_title = Column(String(255), nullable=False, index=True)
    canonical_url = Column(String(1000), nullable=False, unique=True, index=True)
    application_url = Column(String(1000), nullable=True)
    employment_type = Column(String(100), default="Full-time")
    location_restrictions = Column(String(255), default="Unknown")
    geographic_eligibility = Column(String(100), default="Unknown", nullable=False)
    nepal_eligible = Column(Boolean, default=False, nullable=False)
    salary_range = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    experience_level = Column(String(100), nullable=True)  # Junior, Mid, Senior, Lead
    status = Column(String(50), default="Active", nullable=False)  # Active, Expired, Applied, Archived
    match_score = Column(Float, nullable=True)
    match_reasons = Column(JSON, default=list)
    date_discovered = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="jobs")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    outreach_messages = relationship("OutreachMessage", back_populates="job")

    __table_args__ = (
        Index("idx_company_title", "company_id", "normalized_title"),
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(100), nullable=False, index=True)
    is_required = Column(Boolean, default=True)

    job = relationship("Job", back_populates="skills")


# ----------------------------------------------------
# Outreach Models
# ----------------------------------------------------
class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("company_contacts.id", ondelete="SET NULL"), nullable=True)
    template_type = Column(String(100), default="General Introduction")  # Founder, Eng Manager, Recruiter, Follow-up
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default="Draft Generated", nullable=False)
    # Statuses: Discovered, Researching, Ready for outreach, Draft generated, Draft saved, Applied, Follow-up required, Replied, Interviewing, Rejected, Archived
    gmail_draft_id = Column(String(255), nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="outreach_messages")
    events = relationship("OutreachEvent", back_populates="message", cascade="all, delete-orphan")


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    outreach_id = Column(UUID(as_uuid=True), ForeignKey("outreach_messages.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)  # Created, Updated, Saved to Gmail, Exported EML, Status Changed
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    message = relationship("OutreachMessage", back_populates="events")


# ----------------------------------------------------
# Usage, Logs & Settings
# ----------------------------------------------------
class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    provider = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)
    purpose = Column(String(100), nullable=True)  # company_research, email_generation, matching
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DiscoverySource(Base):
    __tablename__ = "discovery_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # RSS, JSON_API, HTML
    endpoint_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    domain = Column(String(255), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)  # If sensitive, stored encrypted
    is_encrypted = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
