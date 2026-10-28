from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable, Mapping

from cue.agents.common.llm import structured
from cue.agents.writer import write_brief
from cue.guards import Drop
from cue.guards.content import remove_explicit
from cue.harness.events import RunEvents
from cue.harness.executor import CallResult, execute
from cue.harness.plan import Plan, PlannedCall
from cue.records import Brief, FitScore, Match
from cue.scoring.fit import score_matches
from cue.scoring.lift import audience_similarity, lift_scores
from cue.identity.musicbrainz import LifeSpan, shared_client
from cue.tools import get_entities, insights
from cue.tools.names import artist_key, normalise_name
from cue.tools.records import Demographics, Entity, EntityRef, InsightsItem, InsightsRequest, InsightsResult

ARTIST = "urn:entity:artist"
UNDER_RADAR_CAP = 0.80
SHORTLIST_LABEL = "Under-the-radar artists"
WIDENED_CAP = 0.85
MIN_ARTISTS = 8
ARTIST_TAKE = 30
GROUP_SIZE = 4
GROUP_TAKE = 50
SHORTLIST = 8
LIFE_CHECKS = 12
GENRE_TAGS = ("urn:tag:genre:qloo", "urn:tag:subgenre:qloo")
STYLE_TAG = "urn:tag:style:qloo"
MAX_GENRES = 3
MAX_STYLES = 3
FILLER_STYLES = {"engaging", "expressive", "dynamic", "innovative", "authentic", "unique", "versatile", "creative", "distinctive", "original"}
ALSO_LISTEN = 2
LLMCall = Callable[..., Awaitable[dict[str, Any]]]


async def similar_productions(production_type: str, production_id: str) -> list[EntityRef]:
    result = await insights(InsightsRequest(production_type, (production_id,), take=GROUP_SIZE + 2))
    return [i.candidate for i in result.items if i.candidate.id != production_id][:GROUP_SIZE]


async def lesser_known_artists(signal_ids: list[str], cap: float) -> InsightsResult:
    return await insights(InsightsRequest(ARTIST, tuple(signal_ids), popularity_max=cap, take=ARTIST_TAKE))


async def artists_group(group_ids: list[str], candidates: InsightsResult) -> InsightsResult:
    if not group_ids:
        raise ValueError("no similar productions to compare with")
    ids = [i.candidate.id for i in candidates.items]
    if not ids:
        return InsightsResult(InsightsRequest(ARTIST))
    return await insights(
        InsightsRequest(ARTIST, tuple(group_ids), popularity_min=0.0, filters={"filter.results.entities": ids}, take=min(len(ids), GROUP_TAKE))
    )


async def demographics(ids: list[str]) -> InsightsResult:
    return await insights(InsightsRequest("urn:demographics", tuple(ids)))


async def life_span(mbids: list[str], name: str) -> LifeSpan | None:
    client = shared_client()
    ids = [m for m in mbids if m]
    if not ids:
        found = await client.find_mbid_by_name(name)
        ids = [found] if found else []
    spans = [span for span in [await client.life_span(m) for m in ids] if span is not None]
    return next((s for s in spans if s.ended), spans[0] if spans else None)


def _distinct(names: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for name in names:
        seen.setdefault(normalise_name(name), name)
    return list(seen.values())


def music_tags(entities: list[Entity]) -> tuple[list[str], list[str]]:
    tags = [t for e in entities for t in e.tags]
    genres = [t.name for kind in GENRE_TAGS for t in tags if t.type == kind]
    words = [t.name.strip().lower() for t in tags if t.type == STYLE_TAG]
    styles = [w for w in words if " " not in w and w not in FILLER_STYLES]
    return _distinct(genres)[:MAX_GENRES], _distinct(styles)[:MAX_STYLES]


def also_listen(explanation: Mapping[str, float], names: Mapping[str, str]) -> list[str]:
    shares = sorted(((score, names[i]) for i, score in explanation.items() if i in names), reverse=True)
    return [name for _, name in shares[:ALSO_LISTEN]]


def merge_same_artist(items: list[InsightsItem]) -> list[InsightsItem]:
    by_key: dict[str, InsightsItem] = {}
    order: list[str] = []
    for item in items:
        key = artist_key(item.candidate.name)
        if key not in by_key:
            by_key[key] = item
            order.append(key)
            continue
        kept = by_key[key]
        best, other = (item, kept) if item.affinity > kept.affinity else (kept, item)
        ids = tuple(dict.fromkeys((*best.duplicate_ids, other.candidate.id, *other.duplicate_ids)))
        by_key[key] = replace(best, duplicate_ids=ids)
    return [by_key[k] for k in order]


SUPERVISOR_TOOLS = {
    "life_span": life_span,
    "similar_productions": similar_productions,
    "lesser_known_artists": lesser_known_artists,
    "artists_group": artists_group,
    "demographics": demographics,
    "get_entities": get_entities,
}


@dataclass(frozen=True)
class SupervisorRun:
    brief: Brief
    scores: tuple[FitScore, ...]
    matches: tuple[Match, ...]
    drops: tuple[Drop, ...]
    cap: float


def _ok(results: Mapping[str, CallResult], call_id: str) -> Any:
    result = results.get(call_id)
    return result.value if result is not None and result.status == "ok" else None


def _first_block(result: InsightsResult | None, entity_id: str) -> Demographics | None:
    if result is None:
        return None
    return next((d for d in result.demographics if d.entity_id == entity_id and (d.age or d.gender)), None)


async def run_supervisor(
    production_id: str,
    production_name: str,
    production_type: str,
    events: RunEvents,
    brief: str = "",
    llm: LLMCall = structured,
    tools: Mapping[str, Callable[..., Awaitable[Any]]] = SUPERVISOR_TOOLS,
) -> SupervisorRun:
    plan = Plan(
        (
            PlannedCall("profile", "demographics", {"ids": [production_id]}),
            PlannedCall("similar", "similar_productions", {"production_type": production_type, "production_id": production_id}),
            PlannedCall("artists", "lesser_known_artists", {"signal_ids": [production_id], "cap": UNDER_RADAR_CAP}),
        )
    )
    results = await execute(plan, tools, events)
    cap = UNDER_RADAR_CAP
    found = _ok(results, "artists")
    if found is None or len(found.items) < MIN_ARTISTS:
        cap = WIDENED_CAP
        events.emit(
            "step_end",
            step="widen",
            tool="supervisor",
            status="ok",
            note=f"Only {len(found.items) if found else 0} under-the-radar artists below popularity {UNDER_RADAR_CAP:.2f}; widened the cap to {WIDENED_CAP:.2f}.",
        )
        widened = await execute(Plan((PlannedCall("artists_wide", "lesser_known_artists", {"signal_ids": [production_id], "cap": WIDENED_CAP}),)), tools, events)
        found = _ok(widened, "artists_wide") or found

    items: list[InsightsItem] = [i for i in (found.items if found else ()) if i.candidate.popularity <= cap]
    items, drops = remove_explicit(items)
    items = merge_same_artist(items)
    for drop in drops:
        events.emit("guard_drop", guard=drop.guard, reason=drop.reason, text=drop.text)

    candidate_result = InsightsResult(InsightsRequest(ARTIST), tuple(items))
    similar = _ok(results, "similar") or []
    similar_ids = [s.id for s in similar]
    similar_names = {s.id: s.name for s in similar}
    follow_up = []
    if items:
        follow_up.append(PlannedCall("audiences", "demographics", {"ids": [i.candidate.id for i in items]}))
        follow_up.append(PlannedCall("profiles", "get_entities", {"ids": [x for i in items for x in (i.candidate.id, *i.duplicate_ids)]}))
        if similar_ids:
            follow_up.append(PlannedCall("group", "artists_group", {"group_ids": list(similar_ids), "candidates": candidate_result}))
    audience_calls = await execute(Plan(tuple(follow_up)), tools, events) if follow_up else {}
    viewers = _first_block(_ok(results, "profile"), production_id)
    artist_demo = {d.entity_id: d for d in (_ok(audience_calls, "audiences").demographics if _ok(audience_calls, "audiences") else ())}

    group = _ok(audience_calls, "group") or InsightsResult(InsightsRequest(ARTIST))
    lifts = lift_scores(candidate_result, group)
    matches = [
        Match(production_id, i.candidate, i.affinity, audience=audience_similarity(viewers, artist_demo.get(i.candidate.id)), explanation=i.explanation)
        for i in items
    ]
    scores = score_matches(matches, lifts)
    by_id = {s.match_id: s for s in scores}
    ranked = sorted(
        ((m, by_id[m.match_id]) for m in matches if by_id[m.match_id].status == "ok"),
        key=lambda p: (-p[1].value, -(p[1].inputs.get("lift") or 0), p[0].candidate.name),
    )[:LIFE_CHECKS]

    profiles = {e.ref.id: e for e in (_ok(audience_calls, "profiles") or [])}
    duplicates = {i.candidate.id: i.duplicate_ids for i in items}
    group_explanations = {i.candidate.id: i.explanation for i in group.items}

    def mbids(entity_id: str) -> list[str]:
        ids = (entity_id, *duplicates.get(entity_id, ()))
        return [p.musicbrainz_id for p in (profiles.get(i) for i in ids) if p is not None and p.musicbrainz_id]

    checks = Plan(tuple(PlannedCall(f"life_{n}", "life_span", {"mbids": mbids(m.candidate.id), "name": m.candidate.name}) for n, (m, _) in enumerate(ranked)))
    spans = await execute(checks, tools, events) if checks.calls else {}
    shortlisted: list[tuple[Match, FitScore]] = []
    for n, (match, fit) in enumerate(ranked):
        span = _ok(spans, f"life_{n}")
        if span is not None and span.ended:
            reason = "died or disbanded, per MusicBrainz" + (f" ({span.end[:4]})" if span.end else "")
            drop = Drop("life_span", reason, match.candidate.name)
            drops.append(drop)
            events.emit("guard_drop", guard=drop.guard, reason=drop.reason, text=drop.text)
            continue
        all_ids = (match.candidate.id, *duplicates.get(match.candidate.id, ()))
        candidates = [c for c in (profiles.get(i) for i in all_ids) if c is not None]
        spotify_id = next((c.spotify_id for c in candidates if c.spotify_id), None)
        genres, styles = music_tags(candidates)
        explanation = next((group_explanations[i] for i in all_ids if group_explanations.get(i)), {})
        extra = {
            "life_span": "active" if span is not None else "unverified",
            "spotify_url": f"https://open.spotify.com/artist/{spotify_id}" if spotify_id else None,
            "genres": genres,
            "styles": styles,
            "fans_also_watch": also_listen(explanation, similar_names),
        }
        shortlisted.append((match, replace(fit, inputs={**fit.inputs, **extra})))
        if len(shortlisted) == SHORTLIST:
            break
    ranked = shortlisted

    events.emit("step_start", step="writer", tool="writer", picks=len(ranked))
    written = await write_brief(production_id, production_name, production_type, ranked, llm=llm, brief=brief)
    events.emit("step_end", step="writer", tool="writer", status="ok", artists=len(written.items))
    for drop in written.drops:
        events.emit("guard_drop", guard=drop.guard, reason=drop.reason, text=drop.text)

    result = Brief(run_id=events.run_id, production_id=production_id, artists=written.items)
    events.emit("result", artists=len(result.artists), matches=len(matches), cap=cap, label=SHORTLIST_LABEL)
    return SupervisorRun(result, tuple(scores), tuple(matches), tuple(drops) + written.drops, cap)
