import pytest

from cue.records import Match
from cue.scoring.fit import lift_ranks, score_match, score_matches
from cue.scoring.lift import audience_similarity, lift_scores
from cue.scoring.sections import section_of
from cue.tools.records import Demographics, EntityRef, InsightsItem, InsightsRequest, InsightsResult

REQUEST = InsightsRequest("urn:entity:tv_show", ("A-1",))


def show(entity_id, popularity=0.5):
    return EntityRef(entity_id, f"Show {entity_id}", "urn:entity:tv_show", popularity)


def item(entity_id, affinity, popularity=0.5, duplicates=()):
    return InsightsItem(show(entity_id, popularity), affinity, 1, {}, tuple(duplicates))


def result(*items):
    return InsightsResult(REQUEST, tuple(items))


@pytest.mark.parametrize(
    "popularity, section",
    [(0.99, "big_screen"), (0.90, "big_screen"), (0.8999, "prime_time"), (0.70, "prime_time"), (0.6999, "indie_gems"), (0.0, "indie_gems")],
)
def test_section_boundaries(popularity, section):
    assert section_of(popularity) == section


def test_score_match_combines_lift_rank_and_audience():
    assert score_match(1.0, 1.0) == pytest.approx(1.0)
    assert score_match(1.0, 0.0) == pytest.approx(0.70)
    assert score_match(0.0, 1.0) == pytest.approx(0.30)
    assert score_match(0.5, 0.5) == pytest.approx(0.50)


def test_score_match_shares_the_weight_when_audience_is_missing():
    assert score_match(0.8, None) == pytest.approx(0.8)
    assert score_match(0.0, None) == pytest.approx(0.0)


def test_score_match_without_lift_is_unknown_not_zero():
    assert score_match(None, 0.9) is None
    assert score_match(None, None) is None


def test_score_match_stays_between_zero_and_one():
    for lift_rank in (0.0, 0.25, 0.5, 0.75, 1.0):
        for audience in (None, 0.0, 0.5, 1.0):
            assert 0.0 <= score_match(lift_rank, audience) <= 1.0


def test_lift_is_own_minus_group():
    lifts = lift_scores(result(item("S-1", 0.96), item("S-2", 0.95)), result(item("S-1", 0.96), item("S-2", 0.93)))
    assert lifts == {"S-1": pytest.approx(0.0), "S-2": pytest.approx(0.02)}


def test_lift_uses_the_group_floor_when_the_group_never_saw_the_show():
    lifts = lift_scores(result(item("S-9", 0.95)), result(item("S-1", 0.97), item("S-2", 0.91)))
    assert lifts["S-9"] == pytest.approx(0.04)


def test_lift_matches_through_duplicate_ids():
    lifts = lift_scores(result(item("S-1", 0.95, duplicates=["S-1b"])), result(item("S-1b", 0.90)))
    assert lifts["S-1"] == pytest.approx(0.05)


def test_no_group_means_no_lift():
    assert lift_scores(result(item("S-1", 0.95)), result()) == {"S-1": None}


def test_audience_similarity():
    a = Demographics("A", {"25_to_29": 0.4, "30_to_34": 0.2}, {"male": 0.1, "female": -0.1})
    assert audience_similarity(a, a) == 1.0
    b = Demographics("B", {"25_to_29": -0.4, "30_to_34": -0.2}, {"male": -0.1, "female": 0.1})
    assert audience_similarity(a, b) == pytest.approx(1 - (0.8 + 0.4 + 0.2 + 0.2) / 4 / 2)
    assert audience_similarity(a, None) is None
    assert audience_similarity(a, Demographics("C", {}, {})) is None


def test_lift_ranks_spread_best_to_worst_and_share_ties():
    assert lift_ranks({"a": 0.03, "b": 0.01, "c": -0.01}) == {"a": 1.0, "b": 0.5, "c": 0.0}
    assert lift_ranks({"a": 0.02, "b": 0.02, "c": 0.0}) == {"a": 1.0, "b": 1.0, "c": 0.0}
    assert lift_ranks({"a": 0.05}) == {"a": 1.0}
    assert lift_ranks({"a": 0.01, "b": 0.01}) == {"a": 1.0, "b": 1.0}
    assert lift_ranks({}) == {}


def test_score_matches_ranks_within_each_section_separately():
    matches = [
        Match("A-1", show("big-1", 0.95), 0.96, audience=0.5),
        Match("A-1", show("big-2", 0.93), 0.95, audience=0.5),
        Match("A-1", show("gem-1", 0.50), 0.95, audience=None),
    ]
    lifts = {"big-1": 0.001, "big-2": 0.02, "gem-1": -0.05}
    scores = {s.match_id: s for s in score_matches(matches, lifts)}
    assert scores["A-1:big-2"].inputs["lift_rank"] == 1.0
    assert scores["A-1:big-1"].inputs["lift_rank"] == 0.0
    assert scores["A-1:gem-1"].inputs["section"] == "indie_gems"
    assert scores["A-1:gem-1"].inputs["lift_rank"] == 1.0
    assert scores["A-1:big-2"].value > scores["A-1:big-1"].value


def test_score_matches_marks_missing_lift_insufficient():
    matches = [Match("A-1", show("S-1", 0.5), 0.95, audience=0.9)]
    score = score_matches(matches, {"S-1": None})[0]
    assert score.status == "insufficient_data" and score.value is None


def test_score_matches_is_deterministic():
    matches = [Match("A-1", show(f"S-{i}", 0.5 + i / 100), 0.95, audience=0.5) for i in range(5)]
    lifts = {f"S-{i}": i / 100 for i in range(5)}
    assert score_matches(matches, lifts) == score_matches(matches, lifts)
