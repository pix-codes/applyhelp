import json
import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class JobicySource(BaseDiscoverySource):
    """
    Discovers remote engineering vacancies via Jobicy's official public API:
    https://jobicy.com/api/v2/remote-jobs
    """

    API_URL = "https://jobicy.com/api/v2/remote-jobs?count=50&industry=engineering"

    def __init__(self, client):
        super().__init__("Jobicy", client)

    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        status, content = await self.client.get(self.API_URL)
        if status != 200 or not content:
            logger.warning("Failed to fetch jobs from Jobicy (status %s)", status)
            return []

        try:
            data = json.loads(content)
            jobs_data = data.get("jobs", [])
        except Exception as e:
            logger.error("Error parsing Jobicy JSON: %s", e)
            return []

        results: list[JobCreate] = []
        for item in jobs_data[:limit]:
            title = item.get("jobTitle", "")
            company_name = item.get("companyName", "")
            job_url = item.get("url", "")
            geo = item.get("jobGeo", "")
            raw_type = item.get("jobType", "Full-time")
            job_type = ", ".join(raw_type) if isinstance(raw_type, list) else str(raw_type)
            description_html = item.get("jobDescription", "") or item.get("jobExcerpt", "")

            # Format salary if present
            salary_min = item.get("annualSalaryMin")
            salary_max = item.get("annualSalaryMax")
            currency = item.get("salaryCurrency", "USD")
            salary_str = None
            if salary_min and salary_max:
                salary_str = f"{currency} {salary_min:,} - {salary_max:,}"
            elif salary_min:
                salary_str = f"{currency} {salary_min:,}+"

            soup = BeautifulSoup(description_html, "html.parser")
            plain_desc = soup.get_text(separator=" ", strip=True)

            eligibility, is_nepal, _ = classify_geographic_eligibility(geo, plain_desc[:500])

            job = JobCreate(
                title=title,
                canonical_url=job_url,
                application_url=job_url,
                company_name=company_name,
                employment_type=job_type,
                location_restrictions=geo or "Unknown",
                geographic_eligibility=eligibility,
                nepal_eligible=is_nepal,
                salary_range=salary_str,
                description=plain_desc[:4000],
                skills=[],
                status="Active",
            )
            results.append(job)

        return results
