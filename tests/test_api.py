import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from cue.api.app import create_app
from cue.api.onboarding import search_types, spotify_id_from
from cue.api.runs import RunManager
from cue.qloo import InMemoryCache, QlooSettings, TokenBucket
from cue.records import Brief, BriefItem, FitScore, Match, PitchItem, PitchKit
from cue.tools.records import EntityRef

SPOTIFY = "0tC995Rfn9k2l7nqgCZsV7"
MBID = "810b210f-b461-4f02-aff2-dff91196147e"


def raw_entity(entity_id, name, kind, spotify=None, mbid=None, popularity=0.5):
    external = {}
    if spotify:
        external["spotify"] = {"id": spotify}
    if mbid:
        external["musicbrainz"] = {"id": mbid}
    return {
        "entity_id": entity_id,
        "name": name,
        "types": [kind],
        "popularity": popularity,
        "properties": {"external": external, "short_description": f"{name} description"},
    }


ARTIST_ENTRY = raw_entity("A-1", "Example Artist", "urn:entity:artist", spotify=SPOTIFY, mbid=MBID, popularity=0.86)
PERSON_ENTRY = raw_entity("P-1", "Example Artist", "urn:entity:person", mbid=MBID, popularity=0.89)
LYRICIST = raw_entity("L-1", "Example Lyricist", "urn:entity:person", mbid="lyricist-mbid", popularity=0.4)


class FakeQloo:
    def __init__(self, routes):
        self.routes = routes
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        for (path, key, value), body in self.routes.items():
            if request.url.path == path and (key is None or request.url.params.get(key) == value):
                return httpx.Response(200, json=body)
        return httpx.Response(200, json={"results": []})


class FakeMusicBrainz:
    def __init__(self, mbid=None):
        self.mbid = mbid
        self.asked = []

    async def find_mbid_for_spotify(self, spotify_id, name=""):
        self.asked.append((spotify_id, name))
        return self.mbid


def manager(routes=None, artist=None, supervisor=None):
    settings = QlooSettings(api_key="test-key", rate_per_s=1000, burst=1000)
    fake = FakeQloo(routes or {})
    kwargs = {"transport": httpx.MockTransport(fake)}
    if artist:
        kwargs["artist"] = artist
    if supervisor:
        kwargs["supervisor"] = supervisor
    return RunManager(settings, InMemoryCache(), TokenBucket(1000, 1000), **kwargs), fake


def wait_for(client, run_id):
    for _ in range(200):
        body = client.get(f"/runs/{run_id}").json()
        if body["status"] != "running":
            return body
        asyncio.run(asyncio.sleep(0.01))
    raise AssertionError("run never finished")


def test_spotify_links_and_ids_parse():
    assert spotify_id_from(f"https://open.spotify.com/artist/{SPOTIFY}?si=abc") == SPOTIFY
    assert spotify_id_from(f"https://open.spotify.com/intl-de/artist/{SPOTIFY}") == SPOTIFY
    assert spotify_id_from(f"spotify:artist:{SPOTIFY}") == SPOTIFY
    assert spotify_id_from(SPOTIFY) == SPOTIFY
    assert spotify_id_from("https://open.spotify.com/track/abc") is None


def test_lyricists_search_people_and_authors():
    assert search_types("lyricist") == ["urn:entity:person", "urn:entity:author"]
    assert search_types("singer") == ["urn:entity:artist"]


def test_route_1_finds_the_artist_by_spotify_and_merges_the_person_entry():
    m, fake = manager(
        {
            ("/entities", "external.spotify.ids", SPOTIFY): {"results": [ARTIST_ENTRY]},
            ("/entities", "external.musicbrainz.ids", MBID): {"results": [ARTIST_ENTRY, PERSON_ENTRY]},
        }
    )
    client = TestClient(create_app(m, FakeMusicBrainz()))
    body = client.post("/onboarding/spotify", json={"link": f"https://open.spotify.com/artist/{SPOTIFY}"}).json()
    assert body["route"] == "spotify"
    assert len(body["candidates"]) == 1
    card = body["candidates"][0]
    assert card["entity_id"] == "A-1" and card["type"] == "urn:entity:artist"
    assert card["related_ids"] == ["P-1"]


def test_route_2_finds_a_lyricist_through_musicbrainz():
    mb = FakeMusicBrainz("lyricist-mbid")
    m, _ = manager({("/entities", "external.musicbrainz.ids", "lyricist-mbid"): {"results": [LYRICIST]}})
    client = TestClient(create_app(m, mb))
    body = client.post("/onboarding/spotify", json={"link": SPOTIFY, "role": "lyricist", "name": "Example Lyricist"}).json()
    assert body["route"] == "musicbrainz"
    assert body["candidates"][0]["entity_id"] == "L-1"
    assert mb.asked == [(SPOTIFY, "Example Lyricist")]


def test_unknown_spotify_artist_points_to_route_3():
    m, _ = manager()
    client = TestClient(create_app(m, FakeMusicBrainz(None)))
    body = client.post("/onboarding/spotify", json={"link": SPOTIFY}).json()
    assert body["route"] is None and body["candidates"] == []
    assert "sound like" in body["note"]


def test_bad_spotify_link_says_so_without_calling_qloo():
    m, fake = manager()
    client = TestClient(create_app(m, FakeMusicBrainz()))
    body = client.post("/onboarding/spotify", json={"link": "https://example.com/me"}).json()
    assert body["route"] is None and "Spotify artist link" in body["note"]
    assert fake.requests == []


def test_name_search_for_a_lyricist_asks_for_people():
    m, fake = manager(
        {
            ("/search", None, None): {"results": [LYRICIST]},
            ("/entities", "entity_ids", "L-1"): {"results": [LYRICIST]},
        }
    )
    client = TestClient(create_app(m, FakeMusicBrainz()))
    body = client.post("/onboarding/name", json={"name": "Example Lyricist", "role": "lyricist"}).json()
    search = next(r for r in fake.requests if r.url.path == "/search")
    assert search.url.params["types"] == "urn:entity:person,urn:entity:author"
    assert body["route"] == "name" and body["candidates"][0]["entity_id"] == "L-1"


def test_sounds_like_keeps_only_exact_matches():
    m, _ = manager(
        {
            ("/search", "query", "Example Artist"): {"results": [ARTIST_ENTRY]},
            ("/entities", "entity_ids", "A-1"): {"results": [ARTIST_ENTRY]},
        }
    )
    client = TestClient(create_app(m, FakeMusicBrainz()))
    body = client.post("/onboarding/sounds-like", json={"names": ["Example Artist", "Nobody Here"]}).json()
    assert body["route"] == "stand_in"
    assert [c["entity_id"] for c in body["candidates"]] == ["A-1"]
    assert body["skipped"] == ["Nobody Here: not in Qloo"]


def fake_artist_run(captured):
    async def run(signal_ids, artist_name, events, brief="", basis="measured"):
        captured.update(signal_ids=signal_ids, artist_name=artist_name, brief=brief, basis=basis)
        events.emit("step_start", step="planner", tool="planner")
        ref = EntityRef("S-1", "Example Show", "urn:entity:tv_show", 0.8)
        fit = FitScore("A-1:S-1", 0.91, "ok", {"section": "prime_time", "lift": 1.4})
        item = PitchItem(ref, fit, "Fans over-index on it.", "Subject", "Body")
        events.emit("result", pitches=1)
        other = EntityRef("G-1", "Example Game", "urn:entity:videogame", 0.6)
        matches = (Match("A-1", ref, 0.9), Match("A-1", other, 0.8))
        scores = (fit, FitScore("A-1:G-1", 0.7, "ok", {"section": "indie_gems", "lift": 0.03, "audience": 0.9}))
        return SimpleNamespace(kit=PitchKit(events.run_id, "A-1", (item,)), matches=matches, scores=scores, drops=(), decisions=())

    return run


def test_artist_run_streams_events_and_returns_sections():
    captured = {}
    m, _ = manager(artist=fake_artist_run(captured))
    with TestClient(create_app(m, FakeMusicBrainz())) as client:
        started = client.post(
            "/runs",
            json={"mode": "artist", "signal_ids": ["A-1"], "artist_name": "Example Artist", "brief": "monsoon romance", "route": "spotify"},
        )
        assert started.status_code == 202
        run_id = started.json()["run_id"]
        done = wait_for(client, run_id)
        assert done["status"] == "done"
        assert done["result"]["sections"]["prime_time"][0]["candidate"]["name"] == "Example Show"
        assert done["result"]["matches_scored"] == 2
        extra = done["result"]["also_love"]
        assert list(extra) == ["urn:entity:videogame"]
        assert extra["urn:entity:videogame"][0]["name"] == "Example Game"
        assert extra["urn:entity:videogame"][0]["lift"] == 0.03
        stream = client.get(f"/runs/{run_id}/events").text
    kinds = [json.loads(line[6:])["kind"] for line in stream.splitlines() if line.startswith("data: ")]
    assert kinds == ["onboarding", "step_start", "result", "run_end"]
    assert captured == {"signal_ids": ["A-1"], "artist_name": "Example Artist", "brief": "monsoon romance", "basis": "measured"}


def test_supervisor_run_returns_the_under_the_radar_label():
    async def run(production_id, production_name, production_type, events, brief="", audiences=None):
        assert production_type == "urn:entity:tv_show"
        assert audiences == ["urn:audience:hobbies_and_interests:video_gamer"]
        ref = EntityRef("A-2", "Quiet Artist", "urn:entity:artist", 0.5)
        item = BriefItem(ref, FitScore("S-1:A-2", 0.8, "ok", {"life_span": "unverified", "spotify_url": None}), "Their fans like it.")
        return SimpleNamespace(brief=Brief(events.run_id, production_id, (item,)), matches=(), drops=(), cap=0.8)

    m, _ = manager(supervisor=run)
    with TestClient(create_app(m, FakeMusicBrainz())) as client:
        run_id = client.post("/runs", json={"mode": "supervisor", "production_id": "S-1", "production_name": "Example Show", "audiences": ["urn:audience:hobbies_and_interests:video_gamer"]}).json()["run_id"]
        done = wait_for(client, run_id)
    assert done["status"] == "done"
    assert done["result"]["label"] == "Under-the-radar artists"
    assert done["result"]["artists"][0]["fit"]["inputs"]["life_span"] == "unverified"


def test_a_failing_run_reports_its_error():
    async def broken(*args, **kwargs):
        raise RuntimeError("Qloo is down")

    m, _ = manager(artist=broken)
    with TestClient(create_app(m, FakeMusicBrainz())) as client:
        run_id = client.post("/runs", json={"mode": "artist", "signal_ids": ["A-1"], "artist_name": "X"}).json()["run_id"]
        done = wait_for(client, run_id)
        stream = client.get(f"/runs/{run_id}/events").text
    assert done["status"] == "error" and "Qloo is down" in done["error"]
    assert "event: error" in stream and "event: run_end" in stream


def test_run_requests_are_checked():
    m, _ = manager()
    client = TestClient(create_app(m, FakeMusicBrainz()))
    assert client.post("/runs", json={"mode": "artist", "artist_name": "X"}).status_code == 422
    assert client.post("/runs", json={"mode": "supervisor", "production_name": "X"}).status_code == 422
    assert client.post("/runs", json={"mode": "dance"}).status_code == 422
    assert client.get("/runs/r_missing").status_code == 404
    assert client.get("/runs/r_missing/events").status_code == 404


def test_health_reports_demo_mode():
    m, _ = manager()
    body = TestClient(create_app(m, FakeMusicBrainz())).get("/health").json()
    assert body == {"ok": True, "demo_mode": False, "runs": 0}


def test_similar_artists_are_the_comparison_group_with_images():
    near = [raw_entity(f"S-{i}", f"Similar {i}", "urn:entity:artist") for i in range(1, 6)]
    near[0]["properties"]["image"] = {"url": "https://images.example/s1.jpg"}
    m, fake = manager(
        {
            ("/v2/insights", "filter.type", "urn:entity:artist"): {"results": {"entities": [ARTIST_ENTRY, *near]}},
            ("/entities", None, None): {"results": list(reversed(near))},
        }
    )
    body = TestClient(create_app(m, FakeMusicBrainz())).get("/artists/A-1/similar").json()
    names = [a["name"] for a in body["artists"]]
    assert "Example Artist" not in names and len(names) == 4
    assert names == ["Similar 1", "Similar 2", "Similar 3", "Similar 4"]
    assert body["artists"][0]["image_url"] == "https://images.example/s1.jpg"


def test_venues_need_a_city_and_ask_qloo_for_live_music_places():
    venue = {"entity_id": "V-1", "name": "Example Hall", "popularity": 0.5, "types": ["urn:entity:place"], "query": {"affinity": 0.9}, "properties": {"address": "1 Main St"}}
    m, fake = manager({("/v2/insights", "filter.type", "urn:entity:place"): {"results": {"entities": [venue]}}})
    client = TestClient(create_app(m, FakeMusicBrainz()))
    assert client.get("/artists/A-1/venues").status_code == 422
    body = client.get("/artists/A-1/venues", params={"city": "Detroit"}).json()
    assert body["venues"][0] == {"id": "V-1", "name": "Example Hall", "address": "1 Main St", "affinity": 0.9, "popularity": 0.5}
    sent = next(r for r in fake.requests if r.url.path == "/v2/insights")
    assert sent.url.params["filter.location.query"] == "Detroit"
    assert sent.url.params["filter.tags"] == "urn:tag:genre:place:live_music_venue"


def test_audiences_are_grouped_by_type_and_keep_only_urn_ids():
    kinds = {"results": {"audience_types": [{"type": "urn:audience:life_stage"}]}}
    page = {"results": {"audiences": [
        {"entity_id": "U-1", "id": "urn:audience:life_stage:new_parents", "name": "New Parents"},
        {"entity_id": "U-2", "id": "U-2", "name": "No Urn"},
    ]}}
    m, fake = manager({("/v2/audiences/types", None, None): kinds, ("/v2/audiences", "filter.parents.types", "urn:audience:life_stage"): page})
    client = TestClient(create_app(m, FakeMusicBrainz()))
    body = client.get("/audiences").json()
    assert body["groups"] == [{"type": "urn:audience:life_stage", "label": "Life stage", "audiences": [{"id": "urn:audience:life_stage:new_parents", "name": "New Parents"}]}]
    asked = len(fake.requests)
    client.get("/audiences")
    assert len(fake.requests) == asked


def test_fan_map_returns_points_and_names_the_hottest_areas():
    squares = [
        {"location": {"latitude": 42.98, "longitude": -85.61}, "query": {"affinity": 1.0, "popularity": 0.9}},
        {"location": {"latitude": 42.3, "longitude": -83.1}, "query": {"affinity": 0.8, "popularity": 0.7}},
        {"location": {"latitude": 10.0, "longitude": -150.0}, "query": {"affinity": 0.9, "popularity": 0.1}},
        {"location": {"latitude": 30.0, "longitude": -90.0}, "query": {"affinity": 0}},
    ]
    m, fake = manager({("/v2/insights", "filter.type", "urn:heatmap"): {"results": {"heatmap": squares}}})
    body = TestClient(create_app(m, FakeMusicBrainz())).get("/artists/A-1/map").json()
    assert body["area"] == "United States"
    assert len(body["points"]) == 3
    assert [a["name"] for a in body["top_areas"]] == ["Grand Rapids, MI", "Detroit, MI"]
    sent = next(r for r in fake.requests if r.url.path == "/v2/insights")
    assert sent.url.params["filter.location.query"] == "United States"


def test_collaborators_keep_similar_sized_active_artists():
    me = raw_entity("A-1", "Example Artist", "urn:entity:artist", popularity=0.5)
    peer = raw_entity("P-2", "Peer Act", "urn:entity:artist", spotify="1" * 22, mbid="mb-peer", popularity=0.55)
    ended = raw_entity("P-3", "Old Act", "urn:entity:artist", mbid="mb-old", popularity=0.45)
    star = raw_entity("P-4", "Huge Star", "urn:entity:artist", popularity=0.99)
    for row, affinity in ((peer, 0.9), (ended, 0.8), (star, 0.95)):
        row["query"] = {"affinity": affinity}
    m, _ = manager(
        {
            ("/v2/insights", "filter.type", "urn:entity:artist"): {"results": {"entities": [star, peer, ended]}},
            ("/entities", "entity_ids", "A-1"): {"results": [me]},
            ("/entities", None, None): {"results": [peer, ended]},
        }
    )

    class Spans(FakeMusicBrainz):
        async def life_span(self, mbid):
            return SimpleNamespace(ended=mbid == "mb-old")

    body = TestClient(create_app(m, Spans())).get("/artists/A-1/collaborators").json()
    assert [a["name"] for a in body["artists"]] == ["Peer Act"]
    assert body["artists"][0]["status"] == "active"
    assert body["artists"][0]["spotify_url"] == "https://open.spotify.com/artist/" + "1" * 22
