from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Company, CompanyContact, CompanyResearch
from app.schemas.company import (
    CompanyContactCreate,
    CompanyCreate,
    CompanyResearchCreate,
)
from app.utils.normalization import normalize_company_name


class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, company_id: UUID) -> Company | None:
        stmt = (
            select(Company)
            .options(
                selectinload(Company.research),
                selectinload(Company.contacts),
                selectinload(Company.jobs),
            )
            .where(Company.id == company_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_normalized_name(self, norm_name: str) -> Company | None:
        stmt = (
            select(Company)
            .options(selectinload(Company.research), selectinload(Company.contacts))
            .where(Company.normalized_name == norm_name)
        )
        return self.db.execute(stmt).scalars().first()

    def get_or_create(self, comp_in: CompanyCreate) -> Company:
        norm = normalize_company_name(comp_in.name)
        existing = self.get_by_normalized_name(norm)
        if existing:
            # Update fields if new info provided
            if comp_in.website_url and not existing.website_url:
                existing.website_url = comp_in.website_url
            if comp_in.careers_url and not existing.careers_url:
                existing.careers_url = comp_in.careers_url
            if comp_in.geographic_eligibility != "Unknown" and existing.geographic_eligibility == "Unknown":
                existing.geographic_eligibility = comp_in.geographic_eligibility
            self.db.commit()
            self.db.refresh(existing)
            return existing

        new_company = Company(
            name=comp_in.name,
            normalized_name=norm,
            website_url=comp_in.website_url,
            careers_url=comp_in.careers_url,
            industry=comp_in.industry,
            company_size=comp_in.company_size,
            remote_policy=comp_in.remote_policy,
            geographic_eligibility=comp_in.geographic_eligibility,
            eligibility_notes=comp_in.eligibility_notes,
            source_name=comp_in.source_name,
        )
        self.db.add(new_company)
        self.db.commit()
        self.db.refresh(new_company)
        return new_company

    def list_companies(self, limit: int = 100, offset: int = 0) -> list[Company]:
        stmt = (
            select(Company)
            .options(selectinload(Company.research), selectinload(Company.contacts))
            .order_by(Company.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def save_research(self, research_in: CompanyResearchCreate) -> CompanyResearch:
        stmt = select(CompanyResearch).where(CompanyResearch.company_id == research_in.company_id)
        existing = self.db.execute(stmt).scalars().first()
        if existing:
            existing.product_summary = research_in.product_summary
            existing.engineering_challenges = research_in.engineering_challenges
            existing.engineering_stack = research_in.engineering_stack
            existing.evidence_urls = research_in.evidence_urls
            existing.raw_scraped_snippet = research_in.raw_scraped_snippet
            self.db.commit()
            self.db.refresh(existing)
            return existing

        new_research = CompanyResearch(**research_in.model_dump())
        self.db.add(new_research)
        self.db.commit()
        self.db.refresh(new_research)
        return new_research

    def add_contact(self, contact_in: CompanyContactCreate, company_id: UUID) -> CompanyContact:
        contact = CompanyContact(company_id=company_id, **contact_in.model_dump())
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact
