from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from cue.agents.common.llm import LLMError, structured
from cue.agents.planner import instructions
from cue.agents.planner.guardrail import Decision, check_decision, default_decision
from cue.harness.events import RunEvents
from cue.harness.executor import CallResult, execute
from cue.harness.plan import Plan, PlannedCall, Ref
from cue.scoring.sections import SECTIONS
from cue.tools import find_tags, insights
from cue.tools.records import InsightsRequest, InsightsResult, TagRef

MAX_ROUNDS = 2
SECTION_TAKE = 10
GROUP_TAKE = 50
GROUP_SIZE = 4
BANDS = {s.name: (s.popularity_min, s.popularity_max) for s in SECTIONS}
MEDIA_TAGS = ("urn:tag:genre:media", "urn:tag:keyword:media")
TAG_VOCABULARY = {
    "tv_show": MEDIA_TAGS,
    "movie": MEDIA_TAGS,
    "videogame": MEDIA_TAGS,
    "podcast": MEDIA_TAGS,
    "brand": ("urn:tag:genre:brand",),
}
LLMCall = Callable[..., Awaitable[dict[str, Any]]]


def entity(production_type: str) -> str:
    return f"urn:entity:{production_type}"


async def similar_artists(signal_ids: list[str]) -> list[str]:
    result = await insights(InsightsRequest("urn:entity:artist", tuple(signal_ids), take=GROUP_SIZE + len(signal_ids) + 2))
    return [i.candidate.id for i in result.items if i.candidate.id not in signal_ids][:GROUP_SIZE]


async def insights_group(production_type: str, group_ids: list[str]) -> InsightsResult:
    if not group_ids:
        raise LLMError("no similar artists to compare with")
    return await insights(InsightsRequest(entity(production_type), tuple(group_ids), popularity_min=0.0, take=GROUP_TAKE))


def _first_fitting_tag(found: list[TagRef], production_type: str) -> str | None:
    vocabulary = TAG_VOCABULARY.get(production_type, ())
    for tag in found:
        if tag.id.startswith(vocabulary):
            return tag.id
    return None


async def insights_section(production_type: str, signal_ids: list[str], section: str, tag_lists: list[list[TagRef]] = ()) -> InsightsResult:
    low, high = BANDS[section]
    tags = tuple(tag for tag in (_first_fitting_tag(found, production_type) for found in tag_lists) if tag)
    return await insights(
        InsightsRequest(entity(production_type), tuple(signal_ids), tags, popularity_min=low, popularity_max=high, take=SECTION_TAKE)
    )


async def demographics(ids: list[str]) -> InsightsResult:
    return await insights(InsightsRequest("urn:demographics", tuple(ids)))


TOOLS = {
    "similar_artists": similar_artists,
    "insights_group": insights_group,
    "insights_section": insights_section,
    "find_tags": find_tags,
    "demographics": demographics,
}


def build_plan(
    decision: Decision,
    signal_ids: list[str],
    already: set[tuple[str, str]],
    have_group: set[str],
    first_round: bool,
    similar_ids: list[str] | None = None,
) -> Plan:
    calls: list[PlannedCall] = []
    if first_round:
        calls.append(PlannedCall("profile", "demographics", {"ids": list(signal_ids)}))
        if decision.use_lift:
            calls.append(PlannedCall("similar", "similar_artists", {"signal_ids": list(signal_ids)}))
    group_source = Ref("similar") if first_round else (list(similar_ids) if similar_ids else None)
    tag_refs = []
    for index, phrase in enumerate(decision.brief_tags if first_round else ()):
        call_id = f"tag_{index}"
        calls.append(PlannedCall(call_id, "find_tags", {"query": phrase}))
        tag_refs.append(Ref(call_id))
    for production_type in decision.production_types:
        wanted = [s for s in decision.sections if (production_type, s) not in already]
        if not wanted:
            continue
        if decision.use_lift and production_type not in have_group and group_source is not None:
            calls.append(PlannedCall(f"group_{production_type}", "insights_group", {"production_type": production_type, "group_ids": group_source}))
        for section in wanted:
            calls.append(
                PlannedCall(
                    f"match_{production_type}_{section}",
                    "insights_section",
                    {"production_type": production_type, "signal_ids": list(signal_ids), "section": section, "tag_lists": tag_refs},
                )
            )
    return Plan(tuple(calls))


def summarise(results: Mapping[str, CallResult]) -> str:
    lines = []
    for call_id, result in results.items():
        if call_id.startswith("match_"):
            count = len(result.value.items) if result.status == "ok" else 0
            lines.append(f"{call_id[6:]}: {count} results" + ("" if result.status == "ok" else f" ({result.status})"))
        elif call_id == "similar":
            lines.append(f"similar artists for lift: {len(result.value) if result.status == 'ok' else 0}")
        elif call_id.startswith("tag_"):
            names = [t.name for t in result.value][:1] if result.status == "ok" else []
            lines.append(f"{call_id}: {names[0] if names else 'no tag found'}")
    return "\n".join(lines)


def _input_block(mode: str, artist_name: str, brief: str, basis: str) -> str:
    return f"<input>\nmode: {mode}\nartist: {artist_name}\nprofile_basis: {basis}\nbrief: {brief or '(none)'}\n</input>"


async def _decide(user: str, already: set[tuple[str, str]], first_round: bool, llm: LLMCall, events: RunEvents) -> Decision:
    try:
        raw = await llm(
            label="planner",
            system=instructions.SYSTEM,
            user=user,
            schema=instructions.schema(),
            prompt_version=instructions.PROMPT_VERSION,
            max_tokens=1500,
        )
        decision = check_decision(raw, already, first_round)
    except LLMError as failure:
        decision = default_decision(str(failure)) if first_round else Decision((), (), done=True, note="Stopped after one round.", fallback=True, problems=(str(failure),))
    events.emit("step_end", step="planner", tool="planner", status="ok", note=decision.note, fallback=decision.fallback, problems=list(decision.problems))
    return decision


@dataclass(frozen=True)
class PlannerOutcome:
    results: dict[str, CallResult]
    decisions: tuple[Decision, ...]


async def run_planner(
    signal_ids: list[str],
    artist_name: str,
    events: RunEvents,
    brief: str = "",
    basis: str = "measured",
    mode: str = "artist",
    llm: LLMCall = structured,
    tools: Mapping[str, Callable[..., Awaitable[Any]]] = TOOLS,
) -> PlannerOutcome:
    results: dict[str, CallResult] = {}
    decisions: list[Decision] = []
    already: set[tuple[str, str]] = set()
    user = _input_block(mode, artist_name, brief, basis)

    for round_number in range(1, MAX_ROUNDS + 1):
        first = round_number == 1
        events.emit("step_start", step="planner", tool="planner", round=round_number)
        prompt = user if first else f"{user}\n<results>\n{summarise(results)}\n</results>"
        decision = await _decide(prompt, already, first, llm, events)
        decisions.append(decision)
        if not first and decision.done:
            break
        have_group = {cid[6:] for cid, r in results.items() if cid.startswith("group_") and r.status == "ok"}
        similar = results.get("similar")
        similar_ids = similar.value if similar is not None and similar.status == "ok" else None
        plan = build_plan(decision, signal_ids, already, have_group, first, similar_ids)
        if not plan.calls:
            break
        round_results = await execute(plan, tools, events)
        results.update(round_results)
        already |= {(c.args["production_type"], c.args["section"]) for c in plan.calls if c.tool == "insights_section"}
        if first and decision.done:
            break
    return PlannerOutcome(results, tuple(decisions))
