import asyncio
import json

import httpx

from cue.identity.musicbrainz import DEFAULT_USER_AGENT, MusicBrainzClient
from cue.qloo.cache import InMemoryCache
from cue.qloo.ratelimit import TokenBucket

ENDED = {"id": "MB-1", "type": "Person", "life-span": {"begin": "1922-02-04", "end": "2011-01-24", "ended": True}}
ACTIVE = {"id": "MB-2", "type": "Person", "life-span": {"begin": "1992", "end": None, "ended": False}}
URL = {"relations": [{"type": "free streaming", "artist": {"id": "MB-2", "name": "Fake Artist"}}]}


class FakeMB:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        status, body = self.replies.pop(0)
        return httpx.Response(status, content=json.dumps(body))


async def no_sleep(seconds):
    return None


def client(fake, demo=False, cache=None):
    return MusicBrainzClient(cache=cache or InMemoryCache(), limiter=TokenBucket(1000.0, 10, sleep=no_sleep), demo_mode=demo, transport=httpx.MockTransport(fake), sleep=no_sleep)


def test_life_span_reads_ended_artists():
    span = asyncio.run(client(FakeMB([(200, ENDED)])).life_span("MB-1"))
    assert span.ended and span.kind == "Person" and span.end == "2011-01-24"


def test_active_artist_is_not_ended():
    assert asyncio.run(client(FakeMB([(200, ACTIVE)])).life_span("MB-2")).ended is False


def test_requests_send_json_format_and_a_user_agent():
    fake = FakeMB([(200, ACTIVE)])
    asyncio.run(client(fake).life_span("MB-2"))
    request = fake.requests[0]
    assert request.url.params["fmt"] == "json" and request.url.path.endswith("/artist/MB-2")
    assert request.headers["User-Agent"] == DEFAULT_USER_AGENT


def test_second_lookup_comes_from_the_cache():
    fake = FakeMB([(200, ACTIVE)])
    mb = client(fake)

    async def twice():
        await mb.life_span("MB-2")
        return await mb.life_span("MB-2")

    assert asyncio.run(twice()).ended is False and len(fake.requests) == 1


def test_503_is_retried_then_succeeds():
    fake = FakeMB([(503, {}), (200, ACTIVE)])
    assert asyncio.run(client(fake).life_span("MB-2")) is not None and len(fake.requests) == 2


def test_any_failure_means_unknown_not_ended():
    assert asyncio.run(client(FakeMB([(503, {}), (503, {}), (503, {})])).life_span("MB-2")) is None
    assert asyncio.run(client(FakeMB([(500, {})])).life_span("MB-2")) is None
    assert asyncio.run(client(FakeMB([])).life_span("")) is None


def test_404_is_cached_as_unknown():
    fake = FakeMB([(404, {"error": "Not Found"})])
    mb = client(fake)

    async def twice():
        first = await mb.life_span("MB-9")
        return first, await mb.life_span("MB-9")

    assert asyncio.run(twice()) == (None, None) and len(fake.requests) == 1


def test_demo_mode_never_calls_out():
    fake = FakeMB([])
    assert asyncio.run(client(fake, demo=True).life_span("MB-2")) is None and fake.requests == []


def test_find_mbid_by_spotify():
    fake = FakeMB([(200, URL)])
    assert asyncio.run(client(fake).find_mbid_by_spotify("SP-1")) == "MB-2"
    assert fake.requests[0].url.params["resource"] == "https://open.spotify.com/artist/SP-1"
    assert asyncio.run(client(FakeMB([(404, {})])).find_mbid_by_spotify("SP-9")) is None
