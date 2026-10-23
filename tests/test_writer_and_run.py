import asyncio

import pytest

from cue.agents.artist_run import choose_picks, describe_listeners, mean_demographics, run_artist
from cue.agents.writer import ArtistFacts, build_prompt, write_pitches
from cue.agents.writer.instructions import schema
from cue.guards.content import is_explicit, remove_explicit
from cue.harness.events import RunEvents
from cue.records import FitScore, Match
from cue.tools.records import Demographics, EntityRef, InsightsItem, InsightsRequest, InsightsResult

ARTIST = ArtistFacts("A-REAL", "Fake Artist", "measured", "strongest at ages 25–29")


def show(i, pop=0.5, kind="urn:entity:tv_show", name=None):
    return EntityRef(i, name or f"Show {i}", kind, pop)


def pick(i, section="indie_gems", value=0.8, lift_rank=1.0, kind="urn:entity:tv_show"):
    m = Match("A-REAL", show(i, kind=kind), 0.95, audience=0.8)
    return m, FitScore(m.match_id, value, "ok", {"section": section, "lift": 0.01, "lift_rank": lift_rank, "audience": 0.8})


@pytest.mark.parametrize("name, explicit", [("Girls on Porn", True), ("NSFW Talk", True), ("Sex Education", True), ("Sussex Gardens", False), ("Essex Lives", False), ("Masaba Masaba", False)])
def test_content_filter(name, explicit):
    assert is_explicit(name) == explicit


def test_remove_explicit_records_a_drop():
    kept, drops = remove_explicit([InsightsItem(show("1", name="Fake Porn Show"), 0.9, 1, {}), InsightsItem(show("2"), 0.9, 2, {})])
    assert [i.candidate.id for i in kept] == ["2"] and drops[0].guard == "content"


def test_prompt_uses_short_aliases_and_data_tags():
    user, aliases, names = build_prompt(ARTIST, [pick("REAL-1"), pick("REAL-2")])
    assert aliases == {"A-1": "A-REAL", "S-1": "REAL-1", "S-2": "REAL-2"}
    assert "{{S-1}} Show REAL-1" in user and user.startswith("<artist>") and "</matches>" in user
    assert "more than fans of similar artists do" in user and "strongest in its group" not in user and "over-index" not in user


def test_schema_only_allows_given_aliases():
    alias_enum = schema(["S-1", "S-2"])["properties"]["items"]["items"]["properties"]["candidate_id"]["enum"]
    assert alias_enum == ["S-1", "S-2"]


def fake_llm(planner=None, writer=None):
    calls = []

    async def llm(**kwargs):
        calls.append(kwargs)
        if kwargs["label"] == "planner":
            return (planner or [{"production_types": ["tv_show"], "sections": ["big_screen", "indie_gems"], "brief_tags": [], "use_lift": True, "done": True, "note": "n"}]).pop(0)
        return writer(kwargs) if callable(writer) else writer

    llm.calls = calls
    return llm


def test_writer_fills_names_attaches_code_scores_and_guards():
    picks = [pick("REAL-1", value=0.9), pick("REAL-2", value=0.7)]
    reply = {
        "items": [
            {"candidate_id": "S-1", "reason": "Viewers of {{S-1}} over-index on my listeners.", "email_subject": "Music for {{S-1}}", "email_body": "Hi there, {{A-1}} here. My music would suit {{S-1}}. My song was featured in a Netflix film. Happy to share two tracks."},
            {"candidate_id": "S-1", "reason": "dup", "email_subject": "dup", "email_body": "dup"},
            {"candidate_id": "S-2", "reason": "Fits *Imaginary Show* too.", "email_subject": "Hello", "email_body": "Hi there, this could suit {{S-2}}."},
        ]
    }
    out = asyncio.run(write_pitches(ARTIST, picks, llm=fake_llm(writer=reply)))
    first = out.items[0]
    assert first.candidate.id == "REAL-1" and first.candidate.name == "Show REAL-1"
    assert first.fit.value == 0.9
    assert first.email_body == "Hi there, Fake Artist here. My music would suit Show REAL-1. Happy to share two tracks."
    assert first.email_subject == "Music for Show REAL-1"
    assert out.items[1].reason == "People who watch Show REAL-2 like music like yours more than fans of similar artists do."
    assert out.items[1].candidate.id == "REAL-2"
    assert sorted({d.guard for d in out.drops}) == ["claim", "grounding", "writer"]


def test_writer_with_no_picks_makes_no_call():
    llm = fake_llm(writer={"items": []})
    assert asyncio.run(write_pitches(ARTIST, [], llm=llm)).items == ()
    assert llm.calls == []


def test_choose_picks_three_per_section_two_per_type():
    scored = [pick(f"t{i}", "indie_gems", 0.9 - i / 100) for i in range(4)] + [pick("g1", "indie_gems", 0.5, kind="urn:entity:videogame")]
    scored += [pick("b1", "big_screen", 0.6)]
    chosen = [m.candidate.id for m, _ in choose_picks(scored)]
    assert chosen == ["b1", "t0", "t1", "g1"]


def test_listener_description_and_mean():
    a = Demographics("A", {"25_to_29": 0.6, "30_to_34": 0.2, "55_and_older": -0.4}, {"female": 0.3, "male": -0.3})
    assert describe_listeners(a) == "strongest at ages 25–29 and 30–34, lean female"
    assert describe_listeners(None) == "no age or gender data"
    b = Demographics("B", {"25_to_29": 0.2}, {"female": 0.1})
    assert mean_demographics((a, b), "X").age["25_to_29"] == pytest.approx(0.4)
    assert mean_demographics((), "X") is None


def fake_tools():
    def result(kind, items):
        return InsightsResult(InsightsRequest(kind), tuple(items))

    async def similar_artists(signal_ids):
        return ["G-1"]

    async def insights_group(production_type, group_ids):
        return result(f"urn:entity:{production_type}", [InsightsItem(show("big", 0.95), 0.95, 1, {}), InsightsItem(show("gem", 0.5), 0.90, 2, {})])

    async def insights_section(production_type, signal_ids, section, tag_lists=()):
        kind = f"urn:entity:{production_type}"
        if section == "big_screen":
            return result(kind, [InsightsItem(show("big", 0.95), 0.951, 1, {})])
        return result(kind, [InsightsItem(show("gem", 0.5), 0.95, 1, {}), InsightsItem(show("porn", 0.4, name="Fake Porn Pod"), 0.99, 2, {})])

    async def find_tags(query):
        return []

    async def demographics(ids):
        return InsightsResult(InsightsRequest("urn:demographics"), demographics=tuple(Demographics(i, {"25_to_29": 0.5}, {"female": 0.2}) for i in ids))

    return {"similar_artists": similar_artists, "insights_group": insights_group, "insights_section": insights_section, "find_tags": find_tags, "demographics": demographics}


def test_run_artist_end_to_end_with_fakes():
    def writer(kwargs):
        allowed = kwargs["schema"]["properties"]["items"]["items"]["properties"]["candidate_id"]["enum"]
        return {"items": [{"candidate_id": a, "reason": f"{{{{{a}}}}} fits.", "email_subject": f"For {{{{{a}}}}}", "email_body": f"Hi there, my music would suit {{{{{a}}}}}."} for a in allowed]}

    events = []
    run = asyncio.run(run_artist(["A-REAL"], "Fake Artist", RunEvents("r_e2e", events.append), llm=fake_llm(writer=writer), tools=fake_tools()))
    assert {i.candidate.id for i in run.kit.items} == {"big", "gem"}
    assert all("porn" not in m.candidate.id for m in run.matches)
    gem = next(s for s in run.scores if s.match_id == "A-REAL:gem")
    assert gem.inputs["lift"] == pytest.approx(0.05) and gem.inputs["section"] == "indie_gems" and gem.inputs["audience"] == 1.0
    kinds = [e["kind"] for e in events]
    assert kinds[-1] == "result" and "guard_drop" in kinds
    assert all(e["run_id"] == "r_e2e" for e in events)


def test_writer_failure_returns_no_pitches_instead_of_crashing():
    from cue.agents.common.llm import LLMError

    async def broken(**kwargs):
        raise LLMError("writer: ran out of max_tokens before finishing")

    out = asyncio.run(write_pitches(ARTIST, [pick("REAL-1")], llm=broken))
    assert out.items == () and "no pitches written" in out.drops[0].reason
