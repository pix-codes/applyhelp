import logging

import httpx

from app.config.settings import get_settings
from app.services.crawling.cache import MemoryResponseCache
from app.services.crawling.rate_limiter import PerDomainRateLimiter

logger = logging.getLogger(__name__)


class RespectfulHttpClient:
    """
    HTTP Client that enforces respectful crawling:
    - Per-domain rate limits
    - Retry-After and exponential backoff
    - Response caching
    - Connection timeouts
    - Descriptive User-Agent
    """

    def __init__(
        self,
        rate_limiter: PerDomainRateLimiter | None = None,
        cache: MemoryResponseCache | None = None,
    ):
        settings = get_settings()
        self.user_agent = settings.crawl_user_agent
        self.rate_limiter = rate_limiter or PerDomainRateLimiter(
            default_delay=settings.crawl_default_delay,
            max_concurrency_per_domain=settings.crawl_max_concurrent_per_domain,
        )
        self.cache = cache or MemoryResponseCache()
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=30.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def get(self, url: str, use_cache: bool = True) -> tuple[int, str | None]:
        if use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                return 200, cached

        await self.rate_limiter.acquire(url)
        retries = 2
        backoff = 2.0

        for attempt in range(retries + 1):
            try:
                resp = await self.client.get(url)
                retry_after_val = None
                if "Retry-After" in resp.headers:
                    try:
                        retry_after_val = float(resp.headers["Retry-After"])
                    except ValueError:
                        retry_after_val = 5.0

                self.rate_limiter.release(url, retry_after=retry_after_val)

                if resp.status_code == 200:
                    text = resp.text
                    if use_cache:
                        self.cache.set(url, text)
                    return resp.status_code, text

                if resp.status_code == 429 and attempt < retries:
                    logger.warning("Rate limit 429 encountered for %s. Backing off...", url)
                    await self.rate_limiter.acquire(url, custom_delay=retry_after_val or backoff)
                    backoff *= 2
                    continue

                return resp.status_code, None
            except Exception as e:
                logger.error("Error fetching %s (attempt %d): %s", url, attempt, e)
                self.rate_limiter.release(url)
                if attempt == retries:
                    return 500, None

        return 500, None

    async def close(self):
        await self.client.aclose()
