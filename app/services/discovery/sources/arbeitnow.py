import json
import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class ArbeitnowSource(BaseDiscoverySource):
    """
    Discovers remote engineering vacancies via Arbeitnow's public job API:
    https://www.arbeitnow.com/api/job-board-api
    """

    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, client):
        super().__init__("Arbeitnow", client)

    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        status, content = await self.client.get(self.API_URL)
        if status != 200 or not content:
            logger.warning("Failed to fetch jobs from Arbeitnow (status %s)", status)
            return []

        try:
            data = json.loads(content)
            jobs_data = data.get("data", [])
        except Exception as e:
            logger.error("Error parsing Arbeitnow JSON: %s", e)
            return []

        results: list[JobCreate] = []
        for item in jobs_data[:limit]:
            title = item.get("title", "")
            company_name = item.get("company_name", "")
            job_url = item.get("url", "")
            location = item.get("location", "")
            remote = item.get("remote", False)
            description_html = item.get("description", "")
            tags = item.get("tags", [])

            soup = BeautifulSoup(description_html, "html.parser")
            plain_desc = soup.get_text(separator=" ", strip=True)

            loc_str = location if location else ("Remote" if remote else "On-site")
            eligibility, is_nepal, reason = classify_geographic_eligibility(
                loc_str, plain_desc[:500]
            )

            job = JobCreate(
                title=title,
                canonical_url=job_url,
                application_url=job_url,
                company_name=company_name,
                employment_type="Full-time",
                location_restrictions=loc_str,
                geographic_eligibility=eligibility,
                nepal_eligible=is_nepal,
                description=plain_desc[:4000],
                skills=tags,
                status="Active",
            )
            results.append(job)

        return results
