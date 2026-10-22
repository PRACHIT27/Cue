import pytest

from cue.qloo import params
from cue.qloo.errors import ParamRejected


def test_normalize_turns_values_into_query_strings():
    assert params.normalize(
        {"feature.explainability": True, "signal.interests.entities": ["a", "b"], "take": 20, "skip": None}
    ) == {"feature.explainability": "true", "signal.interests.entities": "a,b", "take": "20"}


def test_tv_show_accepts_its_year_filters():
    params.check(
        params.INSIGHTS,
        {
            "filter.type": "urn:entity:tv_show",
            "filter.latest_known_year.min": "2022",
            "filter.popularity.max": "0.8",
            "signal.interests.entities": "abc",
            "feature.explainability": "true",
        },
    )


def test_movie_accepts_release_year():
    params.check(params.INSIGHTS, {"filter.type": "urn:entity:movie", "filter.release_year.min": "2015"})


@pytest.mark.parametrize(
    "filter_type",
    ["artist", "book", "brand", "movie", "person", "place", "podcast", "tv_show", "videogame"],
)
def test_popularity_max_works_for_every_entity_type_we_query(filter_type):
    params.check(params.INSIGHTS, {"filter.type": f"urn:entity:{filter_type}", "filter.popularity.max": "0.8"})


def test_rejects_a_parameter_qloo_would_silently_ignore():
    with pytest.raises(ParamRejected) as caught:
        params.check(params.INSIGHTS, {"filter.type": "urn:entity:artist", "filter.release_year.min": "2015"})
    assert "filter.release_year.min is not supported for filter.type urn:entity:artist" in caught.value.reasons


def test_video_game_spelling_gets_a_hint():
    with pytest.raises(ParamRejected) as caught:
        params.check(params.INSIGHTS, {"filter.type": "urn:entity:video_game"})
    assert "use urn:entity:videogame" in str(caught.value)


def test_insights_needs_a_filter_type():
    with pytest.raises(ParamRejected, match="filter.type"):
        params.check(params.INSIGHTS, {"signal.interests.entities": "abc"})


def test_destination_needs_a_signal_entity():
    with pytest.raises(ParamRejected, match="signal.interests.entities"):
        params.check(params.INSIGHTS, {"filter.type": "urn:entity:destination"})


def test_tag_demographics_and_heatmap_take_signals():
    for filter_type in ("urn:tag", "urn:demographics", "urn:heatmap"):
        params.check(params.INSIGHTS, {"filter.type": filter_type, "signal.interests.entities": "abc"})
    params.check(params.INSIGHTS, {"filter.type": "urn:heatmap", "output.heatmap.boundary": "city"})


def test_search_needs_a_query_and_rejects_insights_params():
    params.check(params.SEARCH, {"query": "Prateek Kuhad", "types": "urn:entity:artist", "take": "3"})
    with pytest.raises(ParamRejected):
        params.check(params.SEARCH, {"types": "urn:entity:artist"})
    with pytest.raises(ParamRejected, match="filter.type"):
        params.check(params.SEARCH, {"query": "x", "filter.type": "urn:entity:artist"})


def test_compare_needs_both_sides():
    params.check(params.COMPARE, {"a.signal.interests.entities": "a", "b.signal.interests.entities": "b"})
    with pytest.raises(ParamRejected, match="b.signal.interests.entities"):
        params.check(params.COMPARE, {"a.signal.interests.entities": "a"})


def test_trending_needs_an_entity_and_a_window():
    params.check(
        params.TRENDING,
        {"signal.interests.entities": "a", "filter.start_date": "2026-05-07", "filter.end_date": "2026-07-30"},
    )
    with pytest.raises(ParamRejected, match="filter.start_date"):
        params.check(params.TRENDING, {"signal.interests.entities": "a", "filter.end_date": "2026-07-30"})


def test_entities_needs_ids():
    params.check(params.ENTITIES, {"entity_ids": "a,b"})
    params.check(params.ENTITIES, {"external.spotify.ids": "xyz"})
    with pytest.raises(ParamRejected):
        params.check(params.ENTITIES, {})


def test_unknown_endpoint_is_rejected():
    with pytest.raises(ParamRejected, match="unknown endpoint"):
        params.check("/recommendations", {"filter.type": "urn:entity:artist"})
