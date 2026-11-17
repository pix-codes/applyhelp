import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class WeWorkRemotelySource(BaseDiscoverySource):
    """
    Discovers remote engineering openings via We Work Remotely's public RSS feed:
    https://weworkremotely.com/categories/remote-programming-jobs.rss
    """

    RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    def __init__(self, client):
        super().__init__("WeWorkRemotely", client)

    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        status, content = await self.client.get(self.RSS_URL)
        if status != 200 or not content:
            logger.warning("Failed to fetch WWR RSS feed (status %s)", status)
            return []

        try:
            soup = BeautifulSoup(content, "xml")
            items = soup.find_all("item")
        except Exception as e:
            logger.error("Error parsing WWR RSS XML: %s", e)
            return []

        results: list[JobCreate] = []
        for item in items[:limit]:
            raw_title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            desc_html = item.description.text if item.description else ""

            # Titles usually format as "Company Name: Job Title"
            if ":" in raw_title:
                parts = raw_title.split(":", 1)
                company_name = parts[0].strip()
                title = parts[1].strip()
            else:
                company_name = "Tech Startup"
                title = raw_title.strip()

            desc_soup = BeautifulSoup(desc_html, "html.parser")
            plain_desc = desc_soup.get_text(separator=" ", strip=True)

            eligibility, is_nepal, _ = classify_geographic_eligibility("Worldwide", plain_desc[:500])

            job = JobCreate(
                title=title[:250],
                canonical_url=link,
                application_url=link,
                company_name=company_name[:250],
                employment_type="Full-time",
                location_restrictions="Worldwide",
                geographic_eligibility=eligibility,
                nepal_eligible=is_nepal,
                description=plain_desc[:4000],
                skills=[],
                status="Active",
            )
            results.append(job)

        return results
