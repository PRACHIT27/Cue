import asyncio
from datetime import date

from cue.qloo.params import AUDIENCE_TYPES, AUDIENCES, COMPARE, INSIGHTS, TAG_TYPES, TAGS, TRENDING
from cue.tools import (
    compare,
    find_audiences,
    find_tags,
    get_audience_types,
    get_tag_types,
    insights,
    trend_score,
    trending,
    use_client,
)
from cue.tools.records import InsightsRequest, TrendSeries, TrendWeek
from cue.tools.trending import DATA_ENDS


class FakeClient:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def get(self, endpoint, params, run_id=None):
        self.calls.append((endpoint, params))
        return self.reply


def run(client, coro_factory):
    async def go():
        with use_client(client):
            return await coro_factory()

    return asyncio.run(go())


def show(entity_id, name, affinity, popularity=0.5, explain=None):
    query = {"affinity": affinity}
    if explain:
        query["explainability"] = {"signal.interests.entities": [{"entity_id": k, "score": v} for k, v in explain.items()]}
    return {"entity_id": entity_id, "name": name, "types": ["urn:entity:tv_show"], "popularity": popularity, "query": query}


def test_insights_sends_explainability_bands_and_signals():
    client = FakeClient({"results": {"entities": []}})
    request = InsightsRequest(
        filter_type="urn:entity:tv_show",
        signal_entities=("A-1", "A-2"),
        popularity_min=0.7,
        popularity_max=0.9,
        filters={"filter.latest_known_year.min": 2025},
        take=10,
    )
    run(client, lambda: insights(request))
    endpoint, params = client.calls[0]
    assert endpoint == INSIGHTS
    assert params == {
        "filter.type": "urn:entity:tv_show",
        "filter.latest_known_year.min": 2025,
        "signal.interests.entities": ["A-1", "A-2"],
        "feature.explainability": True,
        "take": 10,
        "filter.popularity.min": 0.7,
        "filter.popularity.max": 0.9,
    }


def test_games_get_a_default_popularity_cap():
    client = FakeClient({"results": {"entities": []}})
    run(client, lambda: insights(InsightsRequest(filter_type="urn:entity:videogame", signal_entities=("A-1",))))
    assert client.calls[0][1]["filter.popularity.max"] == 0.90


def test_insights_dedupes_titles_ranks_and_keeps_every_id():
    reply = {
        "results": {
            "entities": [
                show("S-1", "Fake Show", 0.95, explain={"A-1": 0.6, "A-2": 0.4}),
                show("S-2", "Other Show", 0.97),
                show("S-3", "Fake  Show", 0.96),
            ]
        }
    }
    result = run(FakeClient(reply), lambda: insights(InsightsRequest("urn:entity:tv_show", ("A-1",))))
    assert [(i.candidate.id, i.rank) for i in result.items] == [("S-2", 1), ("S-3", 2)]
    assert result.items[1].duplicate_ids == ("S-1",)
    assert result.items[0].explanation == {}


def test_insights_reads_explanation_shares():
    reply = {"results": {"entities": [show("S-1", "Fake Show", 0.95, explain={"A-1": 0.6, "A-2": 0.4})]}}
    item = run(FakeClient(reply), lambda: insights(InsightsRequest("urn:entity:tv_show", ("A-1",)))).items[0]
    assert item.explanation == {"A-1": 0.6, "A-2": 0.4}


def test_insights_demographics_has_no_take_or_explainability():
    reply = {"results": {"demographics": [{"entity_id": "A-1", "query": {"age": {"25_to_29": 0.4}, "gender": {"male": -0.1, "female": 0.1}}}]}}
    client = FakeClient(reply)
    result = run(client, lambda: insights(InsightsRequest("urn:demographics", ("A-1", "A-2"))))
    assert set(client.calls[0][1]) == {"filter.type", "signal.interests.entities"}
    assert result.demographics[0].age == {"25_to_29": 0.4}


def test_insights_heatmap_and_tags():
    heat = {"results": {"heatmap": [{"location": {"latitude": 1.5, "longitude": 2.5, "geohash": "abc"}, "query": {"affinity": 0.9, "popularity": 0.3}}]}}
    point = run(FakeClient(heat), lambda: insights(InsightsRequest("urn:heatmap", ("A-1",)))).heatmap[0]
    assert (point.geohash, point.affinity) == ("abc", 0.9)
    tags = {"results": {"tags": [{"tag_id": "urn:tag:genre:fake", "name": "Fake", "type": "urn:tag:genre", "query": {"affinity": 0.8}}]}}
    tag, score = run(FakeClient(tags), lambda: insights(InsightsRequest("urn:tag", ("A-1",)))).tags[0]
    assert (tag.name, score) == ("Fake", 0.8)


def test_compare_reads_shared_and_each_side():
    reply = {
        "results": {
            "tags": [{"tag_id": "urn:tag:x:shared", "name": "Shared", "type": "urn:tag", "query": {"score": 0.7}}],
            "a": {"tags": [{"tag_id": "urn:tag:x:a", "name": "A only", "type": "urn:tag"}]},
            "b": [{"tag_id": "urn:tag:x:b", "name": "B only", "type": "urn:tag"}],
        }
    }
    client = FakeClient(reply)
    result = run(client, lambda: compare(["A-1"], ["B-1"]))
    assert client.calls[0][0] == COMPARE
    assert [(t.name, s) for t, s in result.shared] == [("Shared", 0.7)]
    assert [t.name for t in result.a_tags] == ["A only"] and [t.name for t in result.b_tags] == ["B only"]


def test_compare_with_nothing_shared_is_empty_not_an_error():
    result = run(FakeClient({"results": {"tags": []}}), lambda: compare(["A-1"], ["B-1"]))
    assert result.shared == () and result.a_tags == ()


def test_trending_asks_for_twelve_weeks_up_to_the_data_end():
    reply = {
        "results": {
            "trending": [
                {"date": "2026-07-27", "population_percentile": 0.6, "population_rank": "10", "population_rank_velocity": -2, "velocity_fold_change": 3},
                {"date": "2026-07-20", "population_percentile": 0.5, "population_rank": "12", "population_rank_velocity": 1, "velocity_fold_change": 1},
            ]
        }
    }
    client = FakeClient(reply)
    series = run(client, lambda: trending("S-1", "urn:entity:tv_show"))
    endpoint, params = client.calls[0]
    assert endpoint == TRENDING
    assert params["filter.end_date"] == DATA_ENDS.isoformat()
    assert params["filter.start_date"] == "2026-04-10"
    assert [w.week_start for w in series.weeks] == [date(2026, 7, 20), date(2026, 7, 27)]
    assert series.as_of == date(2026, 7, 27) and series.weeks[-1].rank == 10


def test_trending_with_no_data_has_no_as_of():
    series = run(FakeClient({"results": {"trending": []}}), lambda: trending("S-1", "urn:entity:tv_show"))
    assert series.weeks == () and series.as_of is None


def week(day, percentile):
    return TrendWeek(date(2026, 7, day), percentile, 1, 0, 0.0)


def test_trend_score():
    assert trend_score(TrendSeries("S-1", None, ())) is None
    assert trend_score(TrendSeries("S-1", None, (week(1, 0.5),))) is None
    assert trend_score(TrendSeries("S-1", None, (week(1, 0.5), week(8, 0.5)))) == 0.5
    assert trend_score(TrendSeries("S-1", None, (week(1, 0.5), week(8, 0.55)))) == 0.75
    assert trend_score(TrendSeries("S-1", None, (week(1, 0.5), week(8, 0.9)))) == 1.0
    assert trend_score(TrendSeries("S-1", None, (week(1, 0.5), week(8, 0.1)))) == 0.0


def test_lookups():
    tags = FakeClient({"results": {"tags": [{"id": "urn:tag:genre:dream_pop", "name": "Dream Pop", "type": "urn:tag:genre:music"}]}})
    assert [t.id for t in run(tags, lambda: find_tags("dream pop", ["urn:tag:genre:music"]))] == ["urn:tag:genre:dream_pop"]
    assert tags.calls[0] == (TAGS, {"filter.query": "dream pop", "take": 20, "filter.tag.types": ["urn:tag:genre:music"]})
    assert run(FakeClient({}), lambda: find_tags("  ")) == []

    types = FakeClient({"results": {"tag_types": [{"type": "urn:tag:a"}, {"type": "urn:tag:a"}, {"type": "urn:tag:b"}]}})
    assert run(types, get_tag_types) == ["urn:tag:a", "urn:tag:b"]
    assert types.calls[0][0] == TAG_TYPES

    audiences = FakeClient({"results": {"audiences": [{"id": "urn:audience:leisure:fake", "name": "Fake", "type": "urn:audience:leisure"}]}})
    assert [a.name for a in run(audiences, lambda: find_audiences("fake"))] == ["Fake"]
    assert audiences.calls[0][0] == AUDIENCES

    audience_types = FakeClient({"results": {"audience_types": [{"type": "urn:audience:leisure"}]}})
    assert run(audience_types, get_audience_types) == ["urn:audience:leisure"]
    assert audience_types.calls[0][0] == AUDIENCE_TYPES


def test_a_section_floor_turns_off_the_default_game_cap():
    client = FakeClient({"results": {"entities": []}})
    run(client, lambda: insights(InsightsRequest(filter_type="urn:entity:videogame", signal_entities=("A-1",), popularity_min=0.9)))
    assert "filter.popularity.max" not in client.calls[0][1]
