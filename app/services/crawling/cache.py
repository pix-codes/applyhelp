import time


class MemoryResponseCache:
    """
    In-memory HTTP response cache with TTL to prevent re-fetching pages repeatedly.
    """

    def __init__(self, default_ttl_seconds: int = 3600 * 24):
        self.ttl = default_ttl_seconds
        self._cache: dict[str, tuple[float, str]] = {}  # url -> (timestamp, content)

    def get(self, url: str) -> str | None:
        if url in self._cache:
            ts, content = self._cache[url]
            if time.time() - ts < self.ttl:
                return content
            else:
                del self._cache[url]
        return None

    def set(self, url: str, content: str) -> None:
        self._cache[url] = (time.time(), content)

    def clear(self) -> None:
        self._cache.clear()
