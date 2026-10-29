import asyncio

from cue.agents.supervisor_run import SHORTLIST_LABEL, UNDER_RADAR_CAP, WIDENED_CAP, run_supervisor
from cue.agents.writer import build_brief_prompt
from cue.identity.musicbrainz import LifeSpan
from cue.harness.events import RunEvents
from cue.records import FitScore, Match
from cue.tools.records import Demographics, Entity, EntityRef, InsightsItem, InsightsRequest, InsightsResult, TagRef

SHOW = "SHOW-1"
TAGS = (
    TagRef("g1", "Indie Folk", "urn:tag:genre:qloo"),
    TagRef("g2", "Indie - Folk", "urn:tag:genre"),
    TagRef("g3", "Americana", "urn:tag:subgenre:qloo"),
    TagRef("s0", "Engaging", "urn:tag:style:qloo"),
    TagRef("s1", "Moody", "urn:tag:style:qloo"),
    TagRef("s2", "Poetic Folk", "urn:tag:style:qloo"),
)


def artist(i, pop, name=None):
    return EntityRef(i, name or f"Artist {i}", "urn:entity:artist", pop)


def fake_tools(artists, wide=None, ended=(), no_mbid=(), ended_by_name=()):
    calls = []

    def result(items):
        return InsightsResult(InsightsRequest("urn:entity:artist"), tuple(items))

    async def similar_productions(production_type, production_id):
        calls.append("similar")
        return [EntityRef("SHOW-2", "Other Show", "urn:entity:tv_show", 0.9), EntityRef("SHOW-3", "Third Show", "urn:entity:tv_show", 0.9)]

    async def lesser_known_artists(signal_ids, cap):
        calls.append(("artists", cap))
        pool = artists if cap == UNDER_RADAR_CAP else (wide or artists)
        return result([InsightsItem(a, aff, n, {}) for n, (a, aff) in enumerate(pool, 1) if a.popularity <= cap + 0.5])

    async def artists_group(group_ids, candidates):
        calls.append(("group", tuple(i.candidate.id for i in candidates.items)))
        return result([InsightsItem(i.candidate, i.affinity - 0.02, 1, {"SHOW-3": 0.3, "SHOW-2": 0.2}) for i in candidates.items])

    async def demographics(ids):
        return InsightsResult(InsightsRequest("urn:demographics"), demographics=tuple(Demographics(i, {"25_to_29": 0.3}, {"female": 0.1}) for i in ids))

    async def get_entities(ids):
        return [Entity(EntityRef(i, f"Artist {i}", "urn:entity:artist", 0.5), spotify_id=f"sp{i}", musicbrainz_id=None if i in no_mbid else f"mb{i}", tags=TAGS) for i in ids]

    async def life_span(mbids, name):
        calls.append(("life", tuple(mbids), name))
        if not mbids:
            if name in ended_by_name:
                return LifeSpan("by-name", "Person", "1938", "2022-05-10", True)
            return None
        spans = [LifeSpan(m, "Person", "1922", "2011-01-24" if m[2:] in ended else None, m[2:] in ended) for m in mbids]
        return next((s for s in spans if s.ended), spans[0])

    tools = {"similar_productions": similar_productions, "lesser_known_artists": lesser_known_artists, "artists_group": artists_group, "demographics": demographics, "get_entities": get_entities, "life_span": life_span}
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
    assert out.cap == UNDER_RADAR_CAP
    assert all(m.candidate.popularity <= UNDER_RADAR_CAP for m in out.matches)
    assert all(i.candidate.popularity <= UNDER_RADAR_CAP for i in out.brief.artists)


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
    assert events[-1]["kind"] == "result" and events[-1]["label"] == SHORTLIST_LABEL


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


def test_artists_who_died_or_disbanded_are_dropped_and_logged():
    tools, calls = fake_tools(many(12), ended={"a0", "a1"})
    out, events = run(tools)
    assert {"a0", "a1"}.isdisjoint({i.candidate.id for i in out.brief.artists})
    assert len(out.brief.artists) == 8
    drops = [d for d in out.drops if d.guard == "life_span"]
    assert len(drops) == 2 and "2011" in drops[0].reason
    assert any(e["kind"] == "guard_drop" and e["guard"] == "life_span" for e in events)


def test_no_mbid_keeps_the_artist_marked_unverified():
    out, _ = run(fake_tools(many(10), no_mbid={"a0"})[0])
    labels = {i.candidate.id: i.fit.inputs["life_span"] for i in out.brief.artists}
    assert labels.get("a0") == "unverified" and labels.get("a1") == "active"


def test_life_span_is_checked_for_at_most_twelve_artists():
    tools, calls = fake_tools(many(30))
    run(tools)
    assert sum(1 for c in calls if isinstance(c, tuple) and c[0] == "life") == 12


def test_honorific_duplicates_merge_and_either_entry_ending_drops_the_artist():
    pool = many(6) + [(artist("dupA", 0.5, "Ustad Fake Khan"), 0.99), (artist("dupB", 0.5, "Fake Khan"), 0.98)]
    out, _ = run(fake_tools(pool, ended={"dupB"})[0])
    names = [m.candidate.name for m in out.matches]
    assert names.count("Ustad Fake Khan") + names.count("Fake Khan") == 1
    assert all(i.candidate.name not in ("Ustad Fake Khan", "Fake Khan") for i in out.brief.artists)
    assert any(d.guard == "life_span" and d.text == "Ustad Fake Khan" for d in out.drops)


def test_name_search_fallback_catches_an_artist_with_no_mbid():
    pool = many(10) + [(artist("nomb", 0.5, "Fake Legend"), 0.99)]
    tools, calls = fake_tools(pool, no_mbid={"nomb"}, ended_by_name={"Fake Legend"})
    out, _ = run(tools)
    assert ("life", (), "Fake Legend") in calls
    assert all(i.candidate.id != "nomb" for i in out.brief.artists)


def test_writer_guessing_how_an_artist_sounds_is_cut_and_logged():
    async def llm(**kwargs):
        allowed = kwargs["schema"]["properties"]["items"]["items"]["properties"]["candidate_id"]["enum"]
        return {"items": [{"candidate_id": a, "reason": f"Fans of {{{{P-1}}}} lean toward {{{{{a}}}}}. Their warm, soulful songs suit a kitchen scene."} for a in allowed]}

    out = asyncio.run(run_supervisor(SHOW, "Fake Show", "urn:entity:tv_show", RunEvents("r_sup", lambda e: None), llm=llm, tools=fake_tools(many(10))[0]))
    assert all("soulful" not in i.reason and i.reason.startswith("Fans of Fake Show") for i in out.brief.artists)
    assert any(d.guard == "claim" and "sounds" in d.reason for d in out.drops)


def test_writer_gets_qloo_genres_styles_and_similar_shows_as_placeholders():
    seen = {}

    async def llm(**kwargs):
        seen["user"] = kwargs["user"]
        return await writer_llm()(**kwargs)

    out = asyncio.run(run_supervisor(SHOW, "Fake Show", "urn:entity:tv_show", RunEvents("r_sup", lambda e: None), llm=llm, tools=fake_tools(many(10))[0]))
    inputs = out.brief.artists[0].fit.inputs
    assert inputs["genres"] == ["Indie Folk", "Americana"] and inputs["styles"] == ["moody"]
    assert inputs["fans_also_watch"] == ["Third Show", "Other Show"]
    assert "Qloo genres: Indie Folk, Americana" in seen["user"] and "fans of {{S-1}} and {{S-2}}" in seen["user"]
    assert "Third Show" not in seen["user"].split("<artists>")[1]


def test_a_description_in_qloo_words_survives_and_one_in_other_words_is_cut():
    async def llm(**kwargs):
        allowed = kwargs["schema"]["properties"]["items"]["items"]["properties"]["candidate_id"]["enum"]
        return {"items": [{"candidate_id": a, "reason": f"{{{{{a}}}}} makes moody, Americana music. Their warm songs suit {{{{P-1}}}}. Fans of {{{{S-1}}}} listen too."} for a in allowed]}

    out = asyncio.run(run_supervisor(SHOW, "Fake Show", "urn:entity:tv_show", RunEvents("r_sup", lambda e: None), llm=llm, tools=fake_tools(many(10))[0]))
    reason = out.brief.artists[0].reason
    assert "moody, Americana music" in reason and "warm" not in reason and "Fans of Third Show listen too." in reason
