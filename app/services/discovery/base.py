from abc import ABC, abstractmethod

from app.schemas.job import JobCreate
from app.services.crawling.client import RespectfulHttpClient


class BaseDiscoverySource(ABC):
    """
    Abstract base class for all job and company discovery sources.
    Uses official JSON APIs, RSS feeds, or structured feeds.
    """

    def __init__(self, name: str, client: RespectfulHttpClient):
        self.name = name
        self.client = client

    @abstractmethod
    async def fetch_jobs(self, limit: int = 50) -> list[JobCreate]:
        """Fetch and parse candidate vacancies from the discovery source."""
