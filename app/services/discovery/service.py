import logging

from sqlalchemy.orm import Session

from app.repositories.job import JobRepository
from app.services.crawling.client import RespectfulHttpClient
from app.services.discovery.base import BaseDiscoverySource
from app.services.discovery.sources.arbeitnow import ArbeitnowSource
from app.services.discovery.sources.hacker_news import HackerNewsHiringSource
from app.services.discovery.sources.jobicy import JobicySource
from app.services.discovery.sources.nodesk import NoDeskSource
from app.services.discovery.sources.real_work_from_anywhere import RealWorkFromAnywhereSource
from app.services.discovery.sources.remoteok import RemoteOKSource
from app.services.discovery.sources.remotive import RemotiveSource
from app.services.discovery.sources.weworkremotely import WeWorkRemotelySource

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Coordinates discovery sources, fetches vacancies, and saves them to the repository.
    """

    def __init__(self, db: Session, client: RespectfulHttpClient | None = None):
        self.db = db
        self.job_repo = JobRepository(db)
        self.client = client or RespectfulHttpClient()
        self.sources: dict[str, BaseDiscoverySource] = {
            "Remotive": RemotiveSource(self.client),
            "Jobicy": JobicySource(self.client),
            "RemoteOK": RemoteOKSource(self.client),
            "RealWorkFromAnywhere": RealWorkFromAnywhereSource(self.client),
            "WeWorkRemotely": WeWorkRemotelySource(self.client),
            "NoDesk": NoDeskSource(self.client),
            "HackerNews": HackerNewsHiringSource(self.client),
            "Arbeitnow": ArbeitnowSource(self.client),
        }

    async def run_discovery(self, source_name: str | None = None, limit_per_source: int = 20) -> int:
        selected_sources = (
            [self.sources[source_name]] if source_name and source_name in self.sources
            else list(self.sources.values())
        )

        total_saved = 0
        for src in selected_sources:
            logger.info("Running discovery source: %s", src.name)
            try:
                jobs = await src.fetch_jobs(limit=limit_per_source)
                for job_data in jobs:
                    self.job_repo.create_or_update(job_data)
                    total_saved += 1
            except Exception as e:
                logger.error("Error running discovery on %s: %s", src.name, e)

        return total_saved
