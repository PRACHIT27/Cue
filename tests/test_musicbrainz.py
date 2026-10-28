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


def search(*artists):
    return {"artists": [{"id": i, "name": n, "aliases": [{"name": a} for a in aliases]} for i, n, aliases in artists]}


def test_name_search_accepts_one_strict_match_ignoring_honorifics():
    fake = FakeMB([(200, search(("MB-7", "Shivkumar Sharma", ["Pt. Shiv Kumar Sharma"]), ("MB-8", "Shiv Kumar Sharma Band", [])))])
    assert asyncio.run(client(fake).find_mbid_by_name("Shiv Kumar Sharma")) == "MB-7"
    assert fake.requests[0].url.params["query"] == 'artist:"shiv kumar sharma"'


def test_name_search_refuses_ambiguous_or_fuzzy_matches():
    twins = FakeMB([(200, search(("MB-1", "Rashid Khan", []), ("MB-2", "Ustad Rashid Khan", [])))])
    assert asyncio.run(client(twins).find_mbid_by_name("Rashid Khan")) is None
    near = FakeMB([(200, search(("MB-3", "Rashid Ali", []),))])
    assert asyncio.run(client(near).find_mbid_by_name("Rashid Khan")) is None
    assert asyncio.run(client(FakeMB([])).find_mbid_by_name("")) is None


def test_spacing_variants_match_and_a_second_spelling_is_tried():
    fake = FakeMB([(200, {"artists": []}), (200, search(("MB-7", "Shivkumar Sharma", []),))])
    assert asyncio.run(client(fake).find_mbid_by_name("Pt. Shiv Kumar Sharma")) == "MB-7"
    assert [r.url.params["query"] for r in fake.requests] == ['artist:"shiv kumar sharma"', 'artist:"shivkumar sharma"']


def test_name_variants():
    from cue.identity.musicbrainz import name_variants

    assert name_variants("Shiv Kumar Sharma") == ["shiv kumar sharma", "shivkumar sharma"]
    assert name_variants("Rashid Khan") == ["rashid khan"]
    assert name_variants("") == []


SPOTIFY_ID = "3GdSQUH1BRtl9UrrtuwJlP"
NAMED = {"artists": [{"id": "MB-3", "name": "Fake Lyricist", "aliases": []}]}
WITH_SPOTIFY = {"id": "MB-3", "relations": [{"url": {"resource": f"https://open.spotify.com/artist/{SPOTIFY_ID}"}}]}
OTHER_SPOTIFY = {"id": "MB-3", "relations": [{"url": {"resource": "https://open.spotify.com/artist/0000000000000000000000"}}]}


def test_spotify_lookup_falls_back_to_a_name_search_that_must_match_the_link():
    fake = FakeMB([(404, {}), (200, NAMED), (200, WITH_SPOTIFY)])
    assert asyncio.run(client(fake).find_mbid_for_spotify(SPOTIFY_ID, "Fake Lyricist")) == "MB-3"


def test_name_search_with_a_different_spotify_link_is_rejected():
    fake = FakeMB([(404, {}), (200, NAMED), (200, OTHER_SPOTIFY)])
    assert asyncio.run(client(fake).find_mbid_for_spotify(SPOTIFY_ID, "Fake Lyricist")) is None


def test_direct_spotify_lookup_needs_no_name():
    fake = FakeMB([(200, URL)])
    assert asyncio.run(client(fake).find_mbid_for_spotify(SPOTIFY_ID)) == "MB-2"
    assert len(fake.requests) == 1
