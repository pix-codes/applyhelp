from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CandidateExperience, CandidateProfile, CandidateProject
from app.schemas.candidate import (
    CandidateExperienceCreate,
    CandidateProfileUpdate,
    CandidateProjectCreate,
)


class CandidateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_profile(self) -> CandidateProfile | None:
        # Return the primary profile
        stmt = (
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.projects),
            )
            .order_by(CandidateProfile.created_at.asc())
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_or_create_default(self) -> CandidateProfile:
        profile = self.get_profile()
        if not profile:
            profile = CandidateProfile(
                full_name="Software Engineer",
                email="engineer@example.com",
                location="Nepal",
                professional_summary="Senior Software Engineer specializing in backend systems, distributed architectures, and Python/cloud infrastructure.",
                technical_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "SQLAlchemy", "System Design"],
                preferred_job_titles=["Senior Software Engineer", "Backend Engineer", "Platform Engineer", "Python Developer"],
                remote_work_preferences="Remote (Worldwide / Nepal eligible)",
                employment_preferences="Full-time, Contract",
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def update_profile(self, profile_id: UUID, updates: CandidateProfileUpdate) -> CandidateProfile:
        profile = self.db.get(CandidateProfile, profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        data = updates.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(profile, key, value)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def add_experience(self, candidate_id: UUID, exp: CandidateExperienceCreate) -> CandidateExperience:
        db_exp = CandidateExperience(candidate_id=candidate_id, **exp.model_dump())
        self.db.add(db_exp)
        self.db.commit()
        self.db.refresh(db_exp)
        return db_exp

    def delete_experience(self, experience_id: UUID) -> None:
        exp = self.db.get(CandidateExperience, experience_id)
        if exp:
            self.db.delete(exp)
            self.db.commit()

    def add_project(self, candidate_id: UUID, proj: CandidateProjectCreate) -> CandidateProject:
        db_proj = CandidateProject(candidate_id=candidate_id, **proj.model_dump())
        self.db.add(db_proj)
        self.db.commit()
        self.db.refresh(db_proj)
        return db_proj

    def delete_project(self, project_id: UUID) -> None:
        proj = self.db.get(CandidateProject, project_id)
        if proj:
            self.db.delete(proj)
            self.db.commit()
