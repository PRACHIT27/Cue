from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Awaitable, Callable, Mapping

import httpx

from cue.qloo import params as qloo_params
from cue.qloo.cache import Cache, InMemoryCache, cache_key, ttl_for
from cue.qloo.errors import DemoCacheMiss, ParamRejected, QlooHTTPError
from cue.qloo.events import CacheState, CallStatus, EventSink, QlooCallEvent, discard, result_count
from cue.qloo.ratelimit import TokenBucket
from cue.qloo.settings import QlooSettings

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class QlooClient:
    def __init__(
        self,
        settings: QlooSettings,
        cache: Cache | None = None,
        limiter: TokenBucket | None = None,
        sink: EventSink = discard,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.perf_counter,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self.settings = settings
        self.cache = cache if cache is not None else InMemoryCache()
        self.limiter = limiter if limiter is not None else TokenBucket(settings.rate_per_s, settings.burst, sleep=sleep)
        self._sink = sink
        self._sleep = sleep
        self._clock = clock
        self._jitter = jitter
        self._http = httpx.AsyncClient(
            base_url=settings.base_url,
            headers={"X-Api-Key": settings.api_key, "Accept": "application/json"},
            timeout=settings.timeout_s,
            transport=transport,
        )

    async def __aenter__(self) -> QlooClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(self, endpoint: str, params: Mapping[str, Any] | None = None, run_id: str | None = None) -> Any:
        started = self._clock()
        query = qloo_params.normalize(params or {})

        def emit(cache: CacheState, status: CallStatus, **extra: Any) -> None:
            self._sink(
                QlooCallEvent(
                    endpoint=endpoint,
                    params=query,
                    ms=round((self._clock() - started) * 1000),
                    cache=cache,
                    status=status,
                    run_id=run_id,
                    **extra,
                )
            )

        try:
            qloo_params.check(endpoint, query)
        except ParamRejected as rejected:
            emit("skipped", "rejected", error=str(rejected))
            raise

        key = cache_key(endpoint, query)
        cached = self.cache.get(key)
        if cached is not None:
            emit("hit", "ok", result_count=result_count(cached))
            return cached

        if self.settings.demo_mode:
            miss = DemoCacheMiss(endpoint, query)
            emit("miss", "error", error=str(miss))
            raise miss

        attempts = 0
        while True:
            attempts += 1
            await self.limiter.acquire()
            try:
                response = await self._http.get(endpoint, params=query)
            except httpx.TransportError as failure:
                if attempts <= self.settings.max_retries:
                    await self._sleep(self._backoff(attempts, None))
                    continue
                emit("miss", "error", attempts=attempts, error=f"network error: {failure}")
                raise QlooHTTPError(endpoint, None, f"network error after {attempts} attempts: {failure}") from failure

            if response.status_code in RETRYABLE_STATUS and attempts <= self.settings.max_retries:
                await self._sleep(self._backoff(attempts, response.headers.get("Retry-After")))
                continue

            if response.is_error:
                message = response.text[:300]
                emit("miss", "error", http_status=response.status_code, attempts=attempts, error=message)
                raise QlooHTTPError(endpoint, response.status_code, message)

            data = response.json()
            self.cache.set(key, data, ttl_for(endpoint))
            emit(
                "miss",
                "ok",
                http_status=response.status_code,
                attempts=attempts,
                result_count=result_count(data),
            )
            return data

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        delay = self.settings.backoff_base_s * (2 ** (attempt - 1)) * (1 + self._jitter())
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        return delay
