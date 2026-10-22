import asyncio
import json

import httpx
import pytest

from cue.qloo import (
    DemoCacheMiss,
    InMemoryCache,
    ParamRejected,
    QlooClient,
    QlooHTTPError,
    QlooSettings,
    SettingsError,
    TokenBucket,
    cache_key,
)
from cue.qloo.params import INSIGHTS, SEARCH

FAKE_SEARCH = {"results": [{"name": "Example Artist", "entity_id": "FAKE-1", "popularity": 0.4}]}
TV_QUERY = {
    "filter.type": "urn:entity:tv_show",
    "signal.interests.entities": "FAKE-1",
    "feature.explainability": True,
}


class Recorder:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        reply = self.responses.pop(0)
        if isinstance(reply, Exception):
            raise reply
        status, body, headers = reply if len(reply) == 3 else (*reply, {})
        return httpx.Response(status, content=json.dumps(body), headers=headers)


async def no_sleep(seconds):
    return None


def make_client(responses, demo_mode=False, cache=None, max_retries=3):
    recorder = Recorder(responses)
    events = []
    settings = QlooSettings(api_key="test-key", demo_mode=demo_mode, max_retries=max_retries, rate_per_s=1000, burst=1000)
    client = QlooClient(
        settings,
        cache=cache,
        sink=events.append,
        transport=httpx.MockTransport(recorder),
        sleep=no_sleep,
        jitter=lambda: 0.0,
    )
    return client, recorder, events


def run(coro):
    return asyncio.run(coro)


def test_sends_key_header_and_query_to_hackathon_url():
    async def go():
        client, recorder, events = make_client([(200, FAKE_SEARCH)])
        async with client:
            data = await client.get(SEARCH, {"query": "Example Artist", "take": 3}, run_id="r_1")
        return data, recorder, events

    data, recorder, events = run(go())
    request = recorder.requests[0]
    assert data == FAKE_SEARCH
    assert request.method == "GET"
    assert request.url.host == "hackathon.api.qloo.com"
    assert request.url.path == "/search"
    assert request.url.params["query"] == "Example Artist"
    assert request.headers["X-Api-Key"] == "test-key"
    assert events[0].cache == "miss" and events[0].status == "ok"
    assert events[0].run_id == "r_1" and events[0].result_count == 1


def test_second_identical_call_is_served_from_cache():
    async def go():
        client, recorder, events = make_client([(200, FAKE_SEARCH)])
        async with client:
            await client.get(INSIGHTS, TV_QUERY)
            reordered = dict(reversed(list(TV_QUERY.items())))
            await client.get(INSIGHTS, reordered)
        return recorder, events

    recorder, events = run(go())
    assert len(recorder.requests) == 1
    assert [event.cache for event in events] == ["miss", "hit"]


def test_rejected_params_never_reach_qloo():
    async def go():
        client, recorder, events = make_client([])
        async with client:
            with pytest.raises(ParamRejected):
                await client.get(INSIGHTS, {"filter.type": "urn:entity:artist", "filter.release_year.min": 2015})
        return recorder, events

    recorder, events = run(go())
    assert recorder.requests == []
    assert events[0].status == "rejected" and events[0].cache == "skipped"


def test_retries_429_then_succeeds():
    async def go():
        client, recorder, events = make_client([(429, {"error": "slow down"}), (200, FAKE_SEARCH)])
        async with client:
            data = await client.get(SEARCH, {"query": "x"})
        return data, recorder, events

    data, recorder, events = run(go())
    assert data == FAKE_SEARCH
    assert len(recorder.requests) == 2
    assert events[-1].attempts == 2


def test_retries_5xx_and_network_errors():
    async def go():
        client, recorder, _ = make_client(
            [(503, {"error": "down"}), httpx.ConnectError("boom"), (200, FAKE_SEARCH)]
        )
        async with client:
            return await client.get(SEARCH, {"query": "x"}), recorder

    data, recorder = run(go())
    assert data == FAKE_SEARCH and len(recorder.requests) == 3


def test_gives_up_after_max_retries():
    async def go():
        client, recorder, events = make_client([(500, {})] * 4, max_retries=3)
        async with client:
            with pytest.raises(QlooHTTPError) as caught:
                await client.get(SEARCH, {"query": "x"})
        return caught.value, recorder, events

    error, recorder, events = run(go())
    assert error.status == 500
    assert len(recorder.requests) == 4
    assert events[-1].status == "error" and events[-1].attempts == 4


def test_no_retry_on_400():
    async def go():
        client, recorder, events = make_client([(400, {"error": "bad"})])
        async with client:
            with pytest.raises(QlooHTTPError) as caught:
                await client.get(SEARCH, {"query": "x"})
        return caught.value, recorder, events

    error, recorder, events = run(go())
    assert error.status == 400
    assert len(recorder.requests) == 1
    assert events[0].http_status == 400


def test_failed_calls_are_not_cached():
    cache = InMemoryCache()

    async def go():
        client, _, _ = make_client([(400, {})], cache=cache)
        async with client:
            with pytest.raises(QlooHTTPError):
                await client.get(SEARCH, {"query": "x"})

    run(go())
    assert len(cache) == 0


def test_demo_mode_serves_cache_and_fails_loudly_on_a_miss():
    cache = InMemoryCache()
    cache.set(cache_key(SEARCH, {"query": "cached"}), FAKE_SEARCH, 60)

    async def go():
        client, recorder, events = make_client([], demo_mode=True, cache=cache)
        async with client:
            hit = await client.get(SEARCH, {"query": "cached"})
            with pytest.raises(DemoCacheMiss):
                await client.get(SEARCH, {"query": "not cached"})
        return hit, recorder, events

    hit, recorder, events = run(go())
    assert hit == FAKE_SEARCH
    assert recorder.requests == []
    assert [(event.cache, event.status) for event in events] == [("hit", "ok"), ("miss", "error")]


def test_backoff_respects_retry_after():
    client, _, _ = make_client([])
    assert client._backoff(1, "7") == 7.0
    assert client._backoff(3, None) == 2.0
    run(client.aclose())


def test_cache_entries_expire():
    now = [1000.0]
    cache = InMemoryCache(clock=lambda: now[0])
    cache.set("k", {"v": 1}, ttl_s=10)
    assert cache.get("k") == {"v": 1}
    now[0] += 10
    assert cache.get("k") is None


def test_cache_key_ignores_param_order_but_not_values():
    assert cache_key(SEARCH, {"query": "a", "take": "3"}) == cache_key(SEARCH, {"take": "3", "query": "a"})
    assert cache_key(SEARCH, {"query": "a"}) != cache_key(SEARCH, {"query": "b"})


def test_token_bucket_waits_when_empty():
    now = [0.0]
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    async def go():
        bucket = TokenBucket(rate_per_s=2, burst=2, clock=lambda: now[0], sleep=fake_sleep)
        for _ in range(3):
            await bucket.acquire()

    run(go())
    assert waits == [0.5]


def test_settings_need_a_key_unless_demo_mode():
    with pytest.raises(SettingsError):
        QlooSettings.from_env({})
    assert QlooSettings.from_env({"DEMO_MODE": "true"}).demo_mode is True
    settings = QlooSettings.from_env({"QLOO_API_KEY": "k", "QLOO_BASE_URL": "https://example.test/"})
    assert settings.base_url == "https://example.test"
