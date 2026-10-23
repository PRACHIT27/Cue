from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx

from cue.qloo.cache import DAY_S, Cache, InMemoryCache
from cue.qloo.ratelimit import TokenBucket
from cue.tools.names import artist_key

BASE_URL = "https://musicbrainz.org/ws/2"
DEFAULT_USER_AGENT = "Cue/0.1 (Qloo Agentic Hackathon; https://github.com/PRACHIT27/Cue)"
CACHE_TTL_S = 30 * DAY_S
MAX_RETRIES = 2
KEY_VERSION = "mb:v1"


@dataclass(frozen=True)
class LifeSpan:
    mbid: str
    kind: str | None
    begin: str | None
    end: str | None
    ended: bool


class MusicBrainzClient:
    def __init__(
        self,
        user_agent: str | None = None,
        cache: Cache | None = None,
        limiter: TokenBucket | None = None,
        demo_mode: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.cache = cache if cache is not None else InMemoryCache()
        self.limiter = limiter if limiter is not None else TokenBucket(1.0, 1, sleep=sleep)
        self.demo_mode = (os.environ.get("DEMO_MODE", "").strip().lower() in {"1", "true", "yes"}) if demo_mode is None else demo_mode
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"User-Agent": user_agent or os.environ.get("MUSICBRAINZ_USER_AGENT") or DEFAULT_USER_AGENT, "Accept": "application/json"},
            timeout=10.0,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        key = f"{KEY_VERSION}:{path}:{sorted(params.items())}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached or None
        if self.demo_mode:
            return None
        for attempt in range(MAX_RETRIES + 1):
            await self.limiter.acquire()
            try:
                response = await self._http.get(path, params={**params, "fmt": "json"})
            except httpx.HTTPError:
                if attempt < MAX_RETRIES:
                    await self._sleep(1.0 + attempt)
                    continue
                return None
            if response.status_code == 404:
                self.cache.set(key, {}, CACHE_TTL_S)
                return None
            if response.status_code in (429, 503) and attempt < MAX_RETRIES:
                await self._sleep(1.0 + attempt)
                continue
            if response.is_error:
                return None
            data = response.json()
            self.cache.set(key, data, CACHE_TTL_S)
            return data
        return None

    async def life_span(self, mbid: str) -> LifeSpan | None:
        if not mbid:
            return None
        data = await self._get(f"/artist/{mbid}", {})
        if not data:
            return None
        span = data.get("life-span") or {}
        return LifeSpan(mbid=mbid, kind=data.get("type"), begin=span.get("begin"), end=span.get("end"), ended=bool(span.get("ended")))

    async def find_mbid_by_name(self, name: str) -> str | None:
        wanted = compact_key(name)
        if not wanted:
            return None
        for variant in name_variants(name):
            data = await self._get("/artist", {"query": f'artist:"{variant}"', "limit": "10"})
            if not data:
                continue
            matches = {
                str(a["id"])
                for a in data.get("artists") or []
                if a.get("id") and any(compact_key(n) == wanted for n in [a.get("name") or "", *[x.get("name") or "" for x in a.get("aliases") or []]])
            }
            if matches:
                return matches.pop() if len(matches) == 1 else None
        return None

    async def find_mbid_by_spotify(self, spotify_id: str) -> str | None:
        if not spotify_id:
            return None
        data = await self._get("/url", {"resource": f"https://open.spotify.com/artist/{spotify_id}", "inc": "artist-rels"})
        if not data:
            return None
        for relation in data.get("relations") or []:
            artist = relation.get("artist") or {}
            if artist.get("id"):
                return str(artist["id"])
        return None


def compact_key(name: str) -> str:
    return artist_key(name).replace(" ", "")


def name_variants(name: str) -> list[str]:
    words = artist_key(name).split()
    variants = [" ".join(words)] if words else []
    if len(words) >= 3:
        variants.append(" ".join([words[0] + words[1], *words[2:]]))
    return variants


_shared: MusicBrainzClient | None = None


def shared_client() -> MusicBrainzClient:
    global _shared
    if _shared is None:
        _shared = MusicBrainzClient()
    return _shared
