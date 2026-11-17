from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Job, JobSkill
from app.repositories.company import CompanyRepository
from app.schemas.company import CompanyCreate
from app.schemas.job import JobCreate
from app.utils.normalization import normalize_job_title


class JobRepository:
    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)

    def get_by_id(self, job_id: UUID) -> Job | None:
        stmt = (
            select(Job)
            .options(selectinload(Job.company), selectinload(Job.skills))
            .where(Job.id == job_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_canonical_url(self, url: str) -> Job | None:
        stmt = (
            select(Job)
            .options(selectinload(Job.company), selectinload(Job.skills))
            .where(Job.canonical_url == url)
        )
        return self.db.execute(stmt).scalars().first()

    def create_or_update(self, job_in: JobCreate) -> Job:
        # First ensure company exists
        company = self.company_repo.get_or_create(
            CompanyCreate(
                name=job_in.company_name,
                website_url=job_in.company_website,
                geographic_eligibility=job_in.geographic_eligibility,
            )
        )

        existing = self.get_by_canonical_url(job_in.canonical_url)
        norm_title = normalize_job_title(job_in.title)

        if existing:
            # Revalidate
            existing.last_verified_at = datetime.utcnow()
            existing.status = job_in.status
            if job_in.description:
                existing.description = job_in.description
            if job_in.salary_range:
                existing.salary_range = job_in.salary_range
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Check duplicate by company + normalized_title
        stmt = (
            select(Job)
            .where(Job.company_id == company.id, Job.normalized_title == norm_title)
        )
        duplicate = self.db.execute(stmt).scalars().first()
        if duplicate:
            duplicate.last_verified_at = datetime.utcnow()
            duplicate.status = job_in.status
            self.db.commit()
            self.db.refresh(duplicate)
            return duplicate

        new_job = Job(
            company_id=company.id,
            title=job_in.title,
            normalized_title=norm_title,
            canonical_url=job_in.canonical_url,
            application_url=job_in.application_url or job_in.canonical_url,
            employment_type=job_in.employment_type,
            location_restrictions=job_in.location_restrictions,
            geographic_eligibility=job_in.geographic_eligibility,
            nepal_eligible=job_in.nepal_eligible,
            salary_range=job_in.salary_range,
            description=job_in.description,
            experience_level=job_in.experience_level,
            status=job_in.status,
            date_discovered=datetime.utcnow(),
            last_verified_at=datetime.utcnow(),
        )
        self.db.add(new_job)
        self.db.flush()

        # Add skills
        for s in job_in.skills:
            clean_s = s.strip()
            if clean_s:
                self.db.add(JobSkill(job_id=new_job.id, skill_name=clean_s, is_required=True))

        self.db.commit()
        self.db.refresh(new_job)
        return new_job

    def list_jobs(
        self,
        nepal_only: bool = False,
        status: str | None = "Active",
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        stmt = (
            select(Job)
            .options(selectinload(Job.company), selectinload(Job.skills))
        )
        if nepal_only:
            stmt = stmt.where(Job.nepal_eligible.is_(True))
        if status:
            stmt = stmt.where(Job.status == status)

        stmt = stmt.order_by(Job.date_discovered.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def update_match_score(self, job_id: UUID, score: float, reasons: list[str]) -> None:
        job = self.db.get(Job, job_id)
        if job:
            job.match_score = score
            job.match_reasons = reasons
            self.db.commit()
