from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Mapping, Protocol

from cue.qloo.params import ENTITIES, SEARCH

DAY_S = 24 * 60 * 60
LOOKUP_TTL_S = 30 * DAY_S
RESPONSE_TTL_S = DAY_S
KEY_VERSION = "qloo:v1"


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl_s: float) -> None: ...


def cache_key(endpoint: str, params: Mapping[str, str]) -> str:
    body = json.dumps({"endpoint": endpoint, "params": dict(sorted(params.items()))}, separators=(",", ":"))
    return f"{KEY_VERSION}:{hashlib.sha256(body.encode()).hexdigest()}"


def ttl_for(endpoint: str) -> float:
    return LOOKUP_TTL_S if endpoint in {SEARCH, ENTITIES} else RESPONSE_TTL_S


class InMemoryCache:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if self._clock() >= expires_at:
            del self._items[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_s: float) -> None:
        self._items[key] = (self._clock() + ttl_s, value)

    def __len__(self) -> int:
        return len(self._items)
