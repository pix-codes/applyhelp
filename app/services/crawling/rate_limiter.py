import asyncio
import time
from urllib.parse import urlparse


class PerDomainRateLimiter:
    """
    In-memory rate limiter per domain.
    Enforces minimum delay between requests and limits concurrency per domain.
    """

    def __init__(self, default_delay: float = 3.0, max_concurrency_per_domain: int = 1):
        self.default_delay = default_delay
        self.max_concurrency = max_concurrency_per_domain
        self.last_request_times: dict[str, float] = {}
        self.semaphores: dict[str, asyncio.Semaphore] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self.semaphores:
            self.semaphores[domain] = asyncio.Semaphore(self.max_concurrency)
        return self.semaphores[domain]

    async def acquire(self, url: str, custom_delay: float | None = None) -> None:
        domain = self._get_domain(url)
        sem = self._get_semaphore(domain)
        await sem.acquire()

        delay = custom_delay if custom_delay is not None else self.default_delay
        last_time = self.last_request_times.get(domain, 0.0)
        elapsed = time.time() - last_time
        if elapsed < delay:
            wait_needed = delay - elapsed
            await asyncio.sleep(wait_needed)

    def release(self, url: str, retry_after: float | None = None) -> None:
        domain = self._get_domain(url)
        now = time.time()
        if retry_after:
            self.last_request_times[domain] = now + retry_after
        else:
            self.last_request_times[domain] = now

        if domain in self.semaphores:
            self.semaphores[domain].release()
