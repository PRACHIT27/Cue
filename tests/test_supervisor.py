import asyncio

from cue.agents.supervisor_run import EMERGING_CAP, WIDENED_CAP, run_supervisor
from cue.agents.writer import build_brief_prompt
from cue.harness.events import RunEvents
from cue.records import FitScore, Match
from cue.tools.records import Demographics, Entity, EntityRef, InsightsItem, InsightsRequest, InsightsResult

SHOW = "SHOW-1"


def artist(i, pop, name=None):
    return EntityRef(i, name or f"Artist {i}", "urn:entity:artist", pop)


def fake_tools(artists, wide=None):
    calls = []

    def result(items):
        return InsightsResult(InsightsRequest("urn:entity:artist"), tuple(items))

    async def similar_productions(production_type, production_id):
        calls.append("similar")
        return ["SHOW-2", "SHOW-3"]

    async def emerging_artists(signal_ids, cap):
        calls.append(("artists", cap))
        pool = artists if cap == EMERGING_CAP else (wide or artists)
        return result([InsightsItem(a, aff, n, {}) for n, (a, aff) in enumerate(pool, 1) if a.popularity <= cap + 0.5])

    async def artists_group(group_ids, candidates):
        calls.append(("group", tuple(i.candidate.id for i in candidates.items)))
        return result([InsightsItem(i.candidate, i.affinity - 0.02, 1, {}) for i in candidates.items])

    async def demographics(ids):
        return InsightsResult(InsightsRequest("urn:demographics"), demographics=tuple(Demographics(i, {"25_to_29": 0.3}, {"female": 0.1}) for i in ids))

    async def get_entities(ids):
        return [Entity(EntityRef(i, f"Artist {i}", "urn:entity:artist", 0.5), spotify_id=f"sp{i}") for i in ids]

    tools = {"similar_productions": similar_productions, "emerging_artists": emerging_artists, "artists_group": artists_group, "demographics": demographics, "get_entities": get_entities}
    return tools, calls


def writer_llm():
    async def llm(**kwargs):
        allowed = kwargs["schema"]["properties"]["items"]["items"]["properties"]["candidate_id"]["enum"]
        return {"items": [{"candidate_id": a, "reason": f"Fans of {{{{{a}}}}} love {{{{P-1}}}}."} for a in allowed]}

    return llm


def run(tools):
    events = []
    out = asyncio.run(run_supervisor(SHOW, "Fake Show", "urn:entity:tv_show", RunEvents("r_sup", events.append), llm=writer_llm(), tools=tools))
    return out, events


def many(n, start_pop=0.4):
    return [(artist(f"a{i}", start_pop + i / 100), 0.95 - i / 1000) for i in range(n)]


def test_no_artist_above_the_cap_ever_appears():
    pool = many(10) + [(artist("famous", 0.97), 0.99)]
    out, _ = run(fake_tools(pool)[0])
    assert out.cap == EMERGING_CAP
    assert all(m.candidate.popularity <= EMERGING_CAP for m in out.matches)
    assert all(i.candidate.popularity <= EMERGING_CAP for i in out.brief.artists)


def test_thin_results_widen_the_cap_and_say_so():
    tools, calls = fake_tools(many(3), wide=many(3) + [(artist("w1", 0.84), 0.93)])
    out, events = run(tools)
    assert out.cap == WIDENED_CAP and ("artists", WIDENED_CAP) in calls
    note = next(e for e in events if e.get("step") == "widen")["note"]
    assert "widened the cap to 0.85" in note
    assert all(m.candidate.popularity <= WIDENED_CAP for m in out.matches)


def test_brief_has_real_names_spotify_links_and_code_scores():
    out, events = run(fake_tools(many(10))[0])
    first = out.brief.artists[0]
    assert first.candidate.id.startswith("a") and "Fake Show" in first.reason and first.candidate.name in first.reason
    assert first.fit.inputs["spotify_url"] == f"https://open.spotify.com/artist/sp{first.candidate.id}"
    assert first.fit.value is not None
    assert len(out.brief.artists) == 8
    assert events[-1]["kind"] == "result"


def test_explicit_artist_names_are_dropped():
    out, _ = run(fake_tools(many(9) + [(artist("x", 0.5, "Porn Star Band"), 0.99)])[0])
    assert all(m.candidate.id != "x" for m in out.matches)
    assert any(d.guard == "content" for d in out.drops)


def test_brief_prompt_uses_aliases_and_data_tags():
    m = Match(SHOW, artist("REAL", 0.5), 0.9, audience=0.7)
    user, aliases, names = build_brief_prompt(SHOW, "Fake Show", "urn:entity:tv_show", [(m, FitScore(m.match_id, 0.8, "ok", {"lift": 0.02, "lift_rank": 1.0, "audience": 0.7}))])
    assert aliases == {"P-1": SHOW, "A-1": "REAL"} and user.startswith("<production>") and "(TV show)" in user


def test_group_is_asked_about_exactly_our_candidates():
    tools, calls = fake_tools(many(10))
    out, _ = run(tools)
    group_ids = next(c[1] for c in calls if isinstance(c, tuple) and c[0] == "group")
    assert set(group_ids) == {m.candidate.id for m in out.matches}
    assert all(s.inputs["lift"] is not None and s.inputs["lift"] > 0 for s in out.scores)
