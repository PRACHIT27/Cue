from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable, Mapping

from cue.agents.common.llm import structured
from cue.agents.planner import TOOLS, Decision, run_planner
from cue.agents.writer import ArtistFacts, write_pitches
from cue.guards import Drop
from cue.guards.content import is_explicit, remove_explicit
from cue.harness.events import RunEvents
from cue.harness.executor import CallResult, execute
from cue.harness.plan import Plan, PlannedCall
from cue.records import FitScore, Match, PitchKit
from cue.scoring.fit import score_matches
from cue.scoring.lift import audience_similarity, lift_scores
from cue.tools import get_entities
from cue.tools.names import normalise_name
from cue.tools.records import Demographics, Entity, InsightsItem, InsightsRequest, InsightsResult

PICKS_PER_SECTION = 3
MAX_PER_TYPE_IN_SECTION = 2
AGE_LABELS = {
    "24_and_younger": "24 and under",
    "25_to_29": "25–29",
    "30_to_34": "30–34",
    "35_to_44": "35–44",
    "45_to_54": "45–54",
    "55_and_older": "55 and over",
}
GENRE_TAGS = ("urn:tag:genre:qloo", "urn:tag:subgenre:qloo", "urn:tag:genre:media")
THEME_TAGS = ("urn:tag:theme:qloo", "urn:tag:emotional_tone:qloo")
MAX_GENRES = 3
MAX_THEMES = 3
ARTIST_TOOLS = {**TOOLS, "get_entities": get_entities}
LLMCall = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ArtistRun:
    kit: PitchKit
    scores: tuple[FitScore, ...]
    matches: tuple[Match, ...]
    drops: tuple[Drop, ...]
    decisions: tuple[Decision, ...]


def _ok(results: Mapping[str, CallResult], call_id: str) -> Any:
    result = results.get(call_id)
    return result.value if result is not None and result.status == "ok" else None


def mean_demographics(blocks: tuple[Demographics, ...], entity_id: str) -> Demographics | None:
    blocks = tuple(b for b in blocks if b.age or b.gender)
    if not blocks:
        return None

    def mean(key: str) -> dict[str, float]:
        names = {k for b in blocks for k in getattr(b, key)}
        return {k: sum(getattr(b, key).get(k, 0.0) for b in blocks) / len(blocks) for k in names}

    return Demographics(entity_id, mean("age"), mean("gender"))


def describe_listeners(profile: Demographics | None) -> str:
    if profile is None:
        return "no age or gender data"
    ages = [AGE_LABELS.get(k, k) for k, v in sorted(profile.age.items(), key=lambda kv: -kv[1]) if v > 0][:2]
    lean = max(profile.gender.items(), key=lambda kv: kv[1], default=(None, 0.0))
    parts = [f"strongest at ages {' and '.join(ages)}" if ages else "no clear age skew"]
    if lean[0] and lean[1] >= 0.1:
        parts.append(f"lean {lean[0]}")
    return ", ".join(parts)


def _pick_names(entity: Entity, kinds: tuple[str, ...], limit: int) -> list[str]:
    seen: dict[str, str] = {}
    for kind in kinds:
        for tag in entity.tags:
            if tag.type == kind and not is_explicit(tag.name) and tag.name.lower() != "podcasts":
                seen.setdefault(normalise_name(tag.name), tag.name)
    return list(seen.values())[:limit]


def production_tags(entity: Entity | None) -> dict[str, list[str]]:
    if entity is None:
        return {"genres": [], "themes": []}
    return {"genres": _pick_names(entity, GENRE_TAGS, MAX_GENRES), "themes": [t.lower() for t in _pick_names(entity, THEME_TAGS, MAX_THEMES)]}


def candidates_by_type(results: Mapping[str, CallResult]) -> dict[str, list[InsightsItem]]:
    by_type: dict[str, dict[str, InsightsItem]] = {}
    for call_id, result in results.items():
        if not call_id.startswith("match_") or result.status != "ok":
            continue
        production_type = result.value.request.filter_type
        bucket = by_type.setdefault(production_type, {})
        for item in result.value.items:
            if item.candidate.id not in bucket or item.affinity > bucket[item.candidate.id].affinity:
                bucket[item.candidate.id] = item
    return {t: list(items.values()) for t, items in by_type.items()}


def choose_picks(scored: list[tuple[Match, FitScore]]) -> list[tuple[Match, FitScore]]:
    picks: list[tuple[Match, FitScore]] = []
    for section in ("big_screen", "prime_time", "indie_gems"):
        ranked = sorted(
            (p for p in scored if p[1].status == "ok" and p[1].inputs.get("section") == section),
            key=lambda p: (-p[1].value, p[0].candidate.name),
        )
        per_type: dict[str, int] = {}
        chosen = 0
        for match, fit in ranked:
            if chosen == PICKS_PER_SECTION:
                break
            if per_type.get(match.candidate.type, 0) == MAX_PER_TYPE_IN_SECTION:
                continue
            per_type[match.candidate.type] = per_type.get(match.candidate.type, 0) + 1
            picks.append((match, fit))
            chosen += 1
    return picks


async def run_artist(
    signal_ids: list[str],
    artist_name: str,
    events: RunEvents,
    brief: str = "",
    basis: str = "measured",
    llm: LLMCall = structured,
    tools: Mapping[str, Callable[..., Awaitable[Any]]] = ARTIST_TOOLS,
) -> ArtistRun:
    source_id = signal_ids[0]
    planned = await run_planner(signal_ids, artist_name, events, brief=brief, basis=basis, llm=llm, tools=tools)
    results = planned.results
    drops: list[Drop] = []

    by_type = candidates_by_type(results)
    for production_type in list(by_type):
        kept, removed = remove_explicit(by_type[production_type])
        by_type[production_type] = kept
        drops += removed
    for drop in drops:
        events.emit("guard_drop", guard=drop.guard, reason=drop.reason, text=drop.text)

    demo_calls = [PlannedCall(f"audience_{t.split(':')[-1]}", "demographics", {"ids": [i.candidate.id for i in items]}) for t, items in by_type.items() if items]
    audience_results = await execute(Plan(tuple(demo_calls)), tools, events) if demo_calls else {}
    profile_value = _ok(results, "profile")
    profile = mean_demographics(profile_value.demographics if profile_value else (), source_id)
    viewer_demographics: dict[str, Demographics] = {}
    for result in audience_results.values():
        if result.status == "ok":
            viewer_demographics.update({d.entity_id: d for d in result.value.demographics})

    matches: list[Match] = []
    lifts: dict[str, float | None] = {}
    for production_type, items in by_type.items():
        group = _ok(results, f"group_{production_type.split(':')[-1]}") or InsightsResult(InsightsRequest(production_type))
        own = InsightsResult(InsightsRequest(production_type), tuple(items))
        lifts.update(lift_scores(own, group))
        for item in items:
            matches.append(
                Match(
                    source_id=source_id,
                    candidate=item.candidate,
                    affinity=item.affinity,
                    audience=audience_similarity(profile, viewer_demographics.get(item.candidate.id)),
                    explanation=item.explanation,
                )
            )
    scores = score_matches(matches, lifts)
    by_match = {s.match_id: s for s in scores}
    scored = [(m, by_match[m.match_id]) for m in matches]

    picks = choose_picks(scored)
    if picks:
        details = await execute(Plan((PlannedCall("pick_tags", "get_entities", {"ids": [m.candidate.id for m, _ in picks]}),)), tools, events)
        entities = {e.ref.id: e for e in (_ok(details, "pick_tags") or [])}
        picks = [(m, replace(f, inputs={**f.inputs, **production_tags(entities.get(m.candidate.id))})) for m, f in picks]
    events.emit("step_start", step="writer", tool="writer", picks=len(picks))
    written = await write_pitches(ArtistFacts(source_id, artist_name, basis, describe_listeners(profile)), picks, llm=llm, brief=brief)
    events.emit("step_end", step="writer", tool="writer", status="ok", pitches=len(written.items))
    for drop in written.drops:
        events.emit("guard_drop", guard=drop.guard, reason=drop.reason, text=drop.text)

    kit = PitchKit(run_id=events.run_id, artist_id=source_id, items=written.items)
    events.emit("result", pitches=len(kit.items), matches=len(matches), dropped=len(drops) + len(written.drops))
    return ArtistRun(kit, tuple(scores), tuple(matches), tuple(drops) + written.drops, planned.decisions)
