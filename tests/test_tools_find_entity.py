import asyncio

import pytest

from cue.qloo.params import ENTITIES, SEARCH
from cue.tools.context import current_client, use_client
from cue.tools.entities import get_entities
from cue.tools.find_entity import find_entity
from cue.tools.parse import entity, entity_ref


class FakeClient:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    async def get(self, endpoint, params, run_id=None):
        self.calls.append((endpoint, params, run_id))
        reply = self.replies[endpoint]
        return reply(params) if callable(reply) else reply


def artist(entity_id, name, popularity=0.5, spotify=None, musicbrainz=None, types=("urn:entity:artist",), akas=()):
    external = {}
    if spotify:
        external["spotify"] = {"id": spotify}
    if musicbrainz:
        external["musicbrainz"] = {"id": musicbrainz}
    return {
        "entity_id": entity_id,
        "name": name,
        "types": list(types),
        "popularity": popularity,
        "properties": {"external": external, "akas": list(akas)},
    }


def run(client, coro_factory):
    async def go():
        with use_client(client, run_id="r_test"):
            return await coro_factory()

    return asyncio.run(go())


def test_exact_match_only_never_the_first_fuzzy_hit():
    client = FakeClient({SEARCH: {"results": [artist("F-1", "Fakename"), artist("F-2", "Other Fakename")]}})
    assert run(client, lambda: find_entity("Fake Artist", ["urn:entity:artist"])) == []


def test_finds_the_exact_name_even_when_it_is_not_first():
    client = FakeClient({SEARCH: {"results": [artist("F-1", "Fake"), artist("F-2", "Fake Artist", 0.4)]}})
    refs = run(client, lambda: find_entity("fake  artist", ["urn:entity:artist"]))
    assert [r.id for r in refs] == ["F-2"]


def test_aka_counts_as_a_match():
    client = FakeClient({SEARCH: {"results": [artist("F-1", "Real Name", akas=["Stage Name"])]}})
    assert [r.id for r in run(client, lambda: find_entity("Stage Name", ["urn:entity:artist"]))] == ["F-1"]


def test_person_entries_are_never_searched_for_artists():
    client = FakeClient({SEARCH: {"results": [artist("F-1", "Fake Artist", types=("urn:entity:person",))]}})
    assert run(client, lambda: find_entity("Fake Artist", ["urn:entity:artist", "urn:entity:person"])) == []
    endpoint, params, run_id = client.calls[0]
    assert params["types"] == ["urn:entity:artist"]
    assert run_id == "r_test"


def test_same_spotify_id_merges_into_one_keeping_the_more_popular():
    hits = [artist("F-1", "Fake Artist", 0.3, spotify="S-1"), artist("F-2", "Fake Artist", 0.8, spotify="S-1")]
    client = FakeClient({SEARCH: {"results": hits}})
    assert [r.id for r in run(client, lambda: find_entity("Fake Artist", ["urn:entity:artist"]))] == ["F-2"]


def test_two_real_namesakes_are_both_returned_most_popular_first():
    hits = [artist("F-1", "Fake Artist", 0.3, spotify="S-1"), artist("F-2", "Fake Artist", 0.8, spotify="S-2")]
    client = FakeClient({SEARCH: {"results": hits}})
    assert [r.id for r in run(client, lambda: find_entity("Fake Artist", ["urn:entity:artist"]))] == ["F-2", "F-1"]


def test_blank_name_makes_no_call():
    client = FakeClient({})
    assert run(client, lambda: find_entity("   ", ["urn:entity:artist"])) == []
    assert client.calls == []


def test_entity_ref_reads_types_list_and_clamps_popularity():
    ref = entity_ref({"entity_id": "F-1", "name": "Fake", "types": ["urn:entity:artist"], "popularity": 1.7})
    assert ref.type == "urn:entity:artist" and ref.popularity == 1.0


def test_entity_without_a_type_is_a_clear_error():
    with pytest.raises(ValueError, match="no type"):
        entity_ref({"entity_id": "F-1", "name": "Fake", "types": []})


def test_entity_reads_external_ids_and_lastfm():
    raw = {
        "entity_id": "F-1",
        "name": "Fake",
        "types": ["urn:entity:artist"],
        "popularity": 0.2,
        "properties": {
            "short_description": "A fake artist.",
            "image": {"url": "https://example.test/f.jpg"},
            "external": {"spotify": {"id": "S-1"}, "musicbrainz": {"id": "M-1"}, "lastfm": {"listeners": 12, "scrobbles": 340}},
        },
        "tags": [{"tag_id": "urn:tag:genre:fake", "name": "Fake Genre", "type": "urn:tag:genre"}],
    }
    record = entity(raw)
    assert (record.spotify_id, record.musicbrainz_id, record.lastfm_listeners, record.lastfm_scrobbles) == ("S-1", "M-1", 12, 340)
    assert record.tags[0].name == "Fake Genre"


def test_entity_tolerates_missing_properties():
    record = entity({"entity_id": "F-1", "name": "Fake", "types": ["urn:entity:tv_show"]})
    assert record.spotify_id is None and record.lastfm_listeners is None and record.tags == ()


def test_get_entities_keeps_order_and_drops_unknown_ids():
    client = FakeClient({ENTITIES: {"results": [artist("F-2", "Two"), artist("F-1", "One")]}})
    records = run(client, lambda: get_entities(["F-1", "F-9", "F-2", "F-1"]))
    assert [r.ref.id for r in records] == ["F-1", "F-2"]
    assert client.calls[0][1] == {"entity_ids": ["F-1", "F-9", "F-2"]}


def test_tools_refuse_to_run_without_a_client():
    with pytest.raises(RuntimeError, match="use_client"):
        current_client()
