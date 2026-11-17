import json
import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class RemoteOKSource(BaseDiscoverySource):
    """
    Discovers remote engineering vacancies via Remote OK's public JSON API:
    https://remoteok.com/api
    """

    API_URL = "https://remoteok.com/api"

    def __init__(self, client):
        super().__init__("RemoteOK", client)

    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        status, content = await self.client.get(self.API_URL)
        if status != 200 or not content:
            logger.warning("Failed to fetch jobs from RemoteOK (status %s)", status)
            return []

        try:
            data = json.loads(content)
            # First item in RemoteOK is usually legal/metadata
            if isinstance(data, list) and data and "legal" in data[0]:
                data = data[1:]
        except Exception as e:
            logger.error("Error parsing RemoteOK JSON: %s", e)
            return []

        results: list[JobCreate] = []
        for item in data[:limit]:
            title = item.get("position", "")
            company_name = item.get("company", "")
            job_url = item.get("url") or item.get("apply_url", "")
            location = item.get("location", "Worldwide")
            tags = item.get("tags", [])
            description_html = item.get("description", "")

            # Salary
            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            salary_str = None
            if salary_min and salary_max:
                salary_str = f"${salary_min:,} - ${salary_max:,}"

            soup = BeautifulSoup(description_html, "html.parser")
            plain_desc = soup.get_text(separator=" ", strip=True)

            eligibility, is_nepal, _ = classify_geographic_eligibility(location, plain_desc[:500])

            job = JobCreate(
                title=title,
                canonical_url=job_url,
                application_url=item.get("apply_url") or job_url,
                company_name=company_name,
                employment_type="Full-time",
                location_restrictions=location or "Worldwide",
                geographic_eligibility=eligibility,
                nepal_eligible=is_nepal,
                salary_range=salary_str,
                description=plain_desc[:4000],
                skills=tags,
                status="Active",
            )
            results.append(job)

        return results
