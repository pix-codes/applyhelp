import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class RealWorkFromAnywhereSource(BaseDiscoverySource):
    """
    Discovers 100% location-independent, global remote opportunities via
    Real Work From Anywhere's public master RSS feed:
    https://www.realworkfromanywhere.com/rss.xml
    All jobs here explicitly allow global/anywhere remote work.
    """

    RSS_URL = "https://www.realworkfromanywhere.com/rss.xml"

    def __init__(self, client):
        super().__init__("RealWorkFromAnywhere", client)

    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        status, content = await self.client.get(self.RSS_URL)
        if status != 200 or not content:
            logger.warning("Failed to fetch RealWorkFromAnywhere RSS feed (status %s)", status)
            return []

        try:
            soup = BeautifulSoup(content, "xml")
            items = soup.find_all("item")
        except Exception as e:
            logger.error("Error parsing RealWorkFromAnywhere XML: %s", e)
            return []

        results: list[JobCreate] = []
        for item in items[:limit]:
            raw_title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            desc_html = item.description.text if item.description else ""

            # Titles usually format as: "Role Name at Company Name"
            if " at " in raw_title:
                parts = raw_title.split(" at ", 1)
                title = parts[0].strip()
                company_name = parts[1].strip()
            elif " - " in raw_title:
                parts = raw_title.split(" - ", 1)
                company_name = parts[0].strip()
                title = parts[1].strip()
            else:
                title = raw_title.strip()
                company_name = "Global Remote Company"

            desc_soup = BeautifulSoup(desc_html, "html.parser")
            plain_desc = desc_soup.get_text(separator=" ", strip=True)

            # This platform specifically verifies true worldwide / anywhere remote work
            eligibility, is_nepal, _ = classify_geographic_eligibility("Worldwide", plain_desc[:500])
            if not is_nepal and eligibility in ["Worldwide", "Unknown"]:
                # High confidence for Nepal since platform explicitly audits worldwide hiring
                is_nepal = True
                eligibility = "Worldwide"

            job = JobCreate(
                title=title[:250],
                canonical_url=link,
                application_url=link,
                company_name=company_name[:250],
                employment_type="Full-time",
                location_restrictions="Worldwide (Work From Anywhere)",
                geographic_eligibility=eligibility,
                nepal_eligible=is_nepal,
                description=plain_desc[:4000],
                skills=[],
                status="Active",
            )
            results.append(job)

        return results
