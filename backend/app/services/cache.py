"""Small in-process TTL cache for quota-limited API calls."""

import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy
from time import monotonic
from typing import Generic, Hashable, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self) -> None:
        self._entries: dict[Hashable, tuple[float, T]] = {}
        self._locks: dict[Hashable, asyncio.Lock] = {}

    async def get_or_set(
        self, key: Hashable, ttl_seconds: float, factory: Callable[[], Awaitable[T]]
    ) -> T:
        entry = self._entries.get(key)
        if entry is not None and entry[0] > monotonic():
            return deepcopy(entry[1])

        # One in-flight request per key prevents refresh bursts from burning quota.
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > monotonic():
                return deepcopy(entry[1])
            value = await factory()
            self._entries[key] = (monotonic() + ttl_seconds, deepcopy(value))
            return deepcopy(value)
