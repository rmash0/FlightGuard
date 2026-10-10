"""Small in-process TTL cache.

Replace uses of this with Role B's `services/cache.py` once that exists.
"""

import time


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, object]] = {}

    def get(self, key: str) -> object | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires, value = item
        if time.monotonic() >= expires:
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: object, ttl_seconds: float) -> None:
        self._items[key] = (time.monotonic() + ttl_seconds, value)

    def clear(self) -> None:
        self._items.clear()
