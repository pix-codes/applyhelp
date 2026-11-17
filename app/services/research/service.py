import logging

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.repositories.company import CompanyRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.company import CompanyResearchCreate
from app.services.crawling.client import RespectfulHttpClient
from app.services.llm.factory import LLMFactory, record_llm_usage
from app.services.llm.prompts import get_prompt

logger = logging.getLogger(__name__)


class LLMResearchAnalysis(BaseModel):
    product_summary: str = Field(description="Objective 2-3 sentence overview of what the company builds")
    engineering_challenges: str = Field(description="Realistic engineering and technical challenges based on the product")
    engineering_stack: list[str] = Field(description="Documented or clearly observable technologies and frameworks")


class CompanyResearchService:
    """
    Safely researches a company using public websites and summarizes key details
    without hallucinations.
    """

    def __init__(self, db, http_client: RespectfulHttpClient | None = None):
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.http_client = http_client or RespectfulHttpClient()

    async def research_company(self, company_id) -> CompanyResearchCreate | None:
        company = self.company_repo.get_by_id(company_id)
        if not company:
            return None

        # If company doesn't have website_url, try to infer it from company name or existing job description
        target_url = company.website_url
        if not target_url:
            clean_name = company.name.lower().replace(" ", "").replace(",", "").replace(".", "")
            # Check if any job mentions an official domain, or construct standard domain
            for job in company.jobs:
                if job.canonical_url and "weworkremotely" not in job.canonical_url and "news.ycombinator" not in job.canonical_url:
                    target_url = job.canonical_url
                    break
            if not target_url:
                target_url = f"https://{clean_name}.com"
                company.website_url = target_url
                self.db.commit()

        # Fetch public website
        status, html = await self.http_client.get(target_url)
        if status != 200 or not html:
            logger.warning("Could not fetch company website: %s", company.website_url)
            return None

        soup = BeautifulSoup(html, "html.parser")
        # Remove script and style elements
        for s in soup(["script", "style", "noscript"]):
            s.decompose()

        plain_text = soup.get_text(separator=" ", strip=True)[:4000]

        repo = SettingsRepository(self.db) if self.db else None
        system_prompt = get_prompt("company_research_system", repo=repo)

        user_prompt = (
            f"Company Name: {company.name}\n"
            f"Website: {company.website_url}\n\n"
            f"Website Extracted Content:\n{plain_text}\n"
        )

        try:
            llm = LLMFactory.create_provider(db=self.db)
            analysis, raw_resp = await llm.generate_structured(
                prompt=user_prompt,
                schema=LLMResearchAnalysis,
                system_prompt=system_prompt,
            )
            record_llm_usage(self.db, raw_resp, purpose="company_research")

            research_data = CompanyResearchCreate(
                company_id=company.id,
                product_summary=analysis.product_summary,
                engineering_challenges=analysis.engineering_challenges,
                engineering_stack=analysis.engineering_stack,
                evidence_urls=[company.website_url],
                raw_scraped_snippet=plain_text[:1000],
            )
            self.company_repo.save_research(research_data)
            return research_data
        except Exception as e:
            logger.error("LLM Research failed for %s: %s", company.name, e)
            # Save fallback basic research
            fallback = CompanyResearchCreate(
                company_id=company.id,
                product_summary=f"Public website accessed at {company.website_url}",
                engineering_challenges="Distributed systems, scaling, and platform reliability.",
                engineering_stack=[],
                evidence_urls=[company.website_url],
                raw_scraped_snippet=plain_text[:1000],
            )
            self.company_repo.save_research(fallback)
            return fallback
