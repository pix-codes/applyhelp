import json
import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class RemotiveSource(BaseDiscoverySource):
    """
    Discovers remote engineering vacancies via Remotive's public public API:
    https://remotive.com/api/remote-jobs?category=software-dev
    """

    API_URL = "https://remotive.com/api/remote-jobs?category=software-dev"

    def __init__(self, client):
        super().__init__("Remotive", client)

    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        status, content = await self.client.get(self.API_URL)
        if status != 200 or not content:
            logger.warning("Failed to fetch jobs from Remotive (status %s)", status)
            return []

        try:
            data = json.loads(content)
            jobs_data = data.get("jobs", [])
        except Exception as e:
            logger.error("Error parsing Remotive JSON: %s", e)
            return []

        results: list[JobCreate] = []
        for item in jobs_data[:limit]:
            title = item.get("title", "")
            company_name = item.get("company_name", "")
            job_url = item.get("url", "")
            candidate_required_location = item.get("candidate_required_location", "")
            salary = item.get("salary", "")
            description_html = item.get("description", "")

            # Strip HTML
            soup = BeautifulSoup(description_html, "html.parser")
            plain_desc = soup.get_text(separator=" ", strip=True)

            tags = item.get("tags", [])

            eligibility, is_nepal, reason = classify_geographic_eligibility(
                candidate_required_location, plain_desc[:500]
            )

            job = JobCreate(
                title=title,
                canonical_url=job_url,
                application_url=job_url,
                company_name=company_name,
                employment_type=item.get("job_type", "Full-time"),
                location_restrictions=candidate_required_location or "Unknown",
                geographic_eligibility=eligibility,
                nepal_eligible=is_nepal,
                salary_range=salary if salary else None,
                description=plain_desc[:4000],  # bounded size
                skills=tags,
                status="Active",
            )
            results.append(job)

        return results
