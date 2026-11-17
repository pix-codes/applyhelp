import json
import logging

from bs4 import BeautifulSoup

from app.schemas.job import JobCreate
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.eligibility import classify_geographic_eligibility

logger = logging.getLogger(__name__)


class HackerNewsHiringSource(BaseDiscoverySource):
    """
    Discovers startup engineering vacancies directly from YC Hacker News
    'Ask HN: Who is hiring?' threads using the official HN Firebase REST API:
    https://hacker-news.firebaseio.com/v0/
    """

    SEARCH_API = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=Ask+HN:+Who+is+hiring&hitsPerPage=1"
    ITEM_API = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

    def __init__(self, client):
        super().__init__("HackerNews", client)

    async def fetch_jobs(self, limit: int = 30) -> list[JobCreate]:
        # 1. Discover latest 'Who is hiring?' thread ID
        status, content = await self.client.get(self.SEARCH_API)
        if status != 200 or not content:
            logger.warning("Failed to locate HN Who is hiring thread")
            return []

        try:
            search_data = json.loads(content)
            hits = search_data.get("hits", [])
            if not hits:
                return []
            thread_id = hits[0].get("objectID")
        except Exception as e:
            logger.error("Error finding HN thread ID: %s", e)
            return []

        # 2. Get thread details to read comment IDs (top-level comments are job openings)
        thread_url = self.ITEM_API.format(item_id=thread_id)
        status, content = await self.client.get(thread_url)
        if status != 200 or not content:
            return []

        try:
            thread_data = json.loads(content)
            kids = thread_data.get("kids", [])[:limit]
        except Exception as e:
            logger.error("Error reading HN comments: %s", e)
            return []

        results: list[JobCreate] = []
        for kid_id in kids:
            kid_url = self.ITEM_API.format(item_id=kid_id)
            k_status, k_content = await self.client.get(kid_url)
            if k_status != 200 or not k_content:
                continue

            try:
                kid_data = json.loads(k_content)
                text_html = kid_data.get("text", "")
                if not text_html or kid_data.get("deleted") or kid_data.get("dead"):
                    continue

                soup = BeautifulSoup(text_html, "html.parser")
                plain_desc = soup.get_text(separator=" ", strip=True)

                # HN Who is Hiring comments follow pattern: "Company | Title | Location | Remote"
                lines = plain_desc.split("\n")
                first_line = lines[0] if lines else plain_desc[:120]
                parts = [p.strip() for p in first_line.split("|")]

                company_name = parts[0] if parts else "Startup via HN"
                title = parts[1] if len(parts) > 1 else "Software Engineer"
                location = parts[2] if len(parts) > 2 else "Remote"

                # Check geographic eligibility
                eligibility, is_nepal, _ = classify_geographic_eligibility(location, plain_desc[:500])

                job_url = f"https://news.ycombinator.com/item?id={kid_id}"

                job = JobCreate(
                    title=title[:250],
                    canonical_url=job_url,
                    application_url=job_url,
                    company_name=company_name[:250],
                    employment_type="Full-time",
                    location_restrictions=location[:250],
                    geographic_eligibility=eligibility,
                    nepal_eligible=is_nepal,
                    description=plain_desc[:4000],
                    skills=[],
                    status="Active",
                )
                results.append(job)
            except Exception as e:
                logger.error("Error parsing HN job comment %s: %s", kid_id, e)

        return results
