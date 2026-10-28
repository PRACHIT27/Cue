from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable

from cue.agents.common.llm import LLMError, _env, structured
from cue.agents.writer import instructions
from cue.agents.writer.guardrail import brief_fallback, check_pitches
from cue.guards import Drop, Known, guard_brief_items
from cue.guards.claims import strip_newness_claims, strip_sound_claims
from cue.records import BriefItem, FitScore, Match, PitchItem

TYPE_LABELS = {
    "urn:entity:tv_show": "TV show",
    "urn:entity:movie": "film",
    "urn:entity:videogame": "video game",
    "urn:entity:podcast": "podcast",
    "urn:entity:brand": "brand",
}
SECTION_LABELS = {"big_screen": "famous", "prime_time": "mid-size", "indie_gems": "smaller"}
LLMCall = Callable[..., Awaitable[dict[str, Any]]]


async def _call(llm: LLMCall, **kwargs: Any) -> dict[str, Any]:
    return await llm(model=_env("LLM_LARGE_MODEL", "claude-haiku-5-5"), **kwargs)


@dataclass(frozen=True)
class ArtistFacts:
    id: str
    name: str
    basis: str
    fans: str


def _match_line(alias: str, match: Match, fit: FitScore) -> str:
    facts = [f"{TYPE_LABELS.get(match.candidate.type, 'production')}, {SECTION_LABELS.get(fit.inputs.get('section'), '')}"]
    lift = fit.inputs.get("lift")
    if lift is not None and lift > 0:
        facts.append("people who watch or play it like this artist's kind of music more than fans of similar artists do")
    audience = fit.inputs.get("audience")
    if audience is not None:
        facts.append(f"age and gender of its audience match the artist's listeners {round(audience * 100)}%")
    return f"- {{{{{alias}}}}} {match.candidate.name}: " + "; ".join(facts)


def build_prompt(artist: ArtistFacts, picks: list[tuple[Match, FitScore]], brief: str = "") -> tuple[str, dict[str, str], dict[str, str]]:
    aliases = {"A-1": artist.id}
    alias_names = {"A-1": artist.name}
    lines = []
    for index, (match, fit) in enumerate(picks, start=1):
        alias = f"S-{index}"
        aliases[alias] = match.candidate.id
        alias_names[alias] = match.candidate.name
        lines.append(_match_line(alias, match, fit))
    user = (
        f"<artist>\n{{{{A-1}}}} {artist.name}\nprofile_basis: {artist.basis}\nlisteners: {artist.fans}\n</artist>\n"
        f"<brief>\n{brief or '(none)'}\n</brief>\n"
        f"<matches>\n" + "\n".join(lines) + "\n</matches>\nWrite one pitch per match."
    )
    return user, aliases, alias_names


@dataclass(frozen=True)
class WriterOutcome:
    items: tuple[PitchItem, ...]
    drops: tuple[Drop, ...]


async def write_pitches(artist: ArtistFacts, picks: list[tuple[Match, FitScore]], llm: LLMCall = structured, brief: str = "") -> WriterOutcome:
    if not picks:
        return WriterOutcome((), ())
    user, aliases, alias_names = build_prompt(artist, picks, brief)
    production_aliases = [a for a in aliases if a.startswith("S-")]
    try:
        raw = await _call(
            llm,
            label="writer",
            system=instructions.SYSTEM,
            user=user,
            schema=instructions.schema(production_aliases),
            prompt_version=instructions.PROMPT_VERSION,
            max_tokens=8000,
        )
    except LLMError as failure:
        return WriterOutcome((), (Drop("writer", f"no pitches written: {failure}", ""),))
    by_alias = {f"S-{i}": pair for i, pair in enumerate(picks, start=1)}
    drafts: list[PitchItem] = []
    drops: list[Drop] = []
    for entry in raw.get("items") or []:
        alias = entry.get("candidate_id")
        if alias not in by_alias:
            drops.append(Drop("writer", f"pitch for unknown placeholder {alias}", str(alias)))
            continue
        match, fit = by_alias[alias]
        drafts.append(
            PitchItem(
                candidate=replace(match.candidate, id=alias),
                fit=fit,
                reason=str(entry.get("reason") or ""),
                email_subject=str(entry.get("email_subject") or ""),
                email_body=str(entry.get("email_body") or ""),
            )
        )
    kept, guard_drops = check_pitches(drafts, aliases, alias_names, artist.name)
    return WriterOutcome(tuple(kept), tuple(drops + guard_drops))


def _artist_line(alias: str, match: Match, fit: FitScore, show_aliases: dict[str, str]) -> str:
    facts = ["a lesser-known artist"]
    if fit.inputs.get("genres"):
        facts.append("Qloo genres: " + ", ".join(fit.inputs["genres"]))
    if fit.inputs.get("styles"):
        facts.append("Qloo style words: " + ", ".join(fit.inputs["styles"]))
    shows = [f"{{{{{show_aliases[n]}}}}}" for n in fit.inputs.get("fans_also_watch") or [] if n in show_aliases]
    if shows:
        facts.append(f"fans of {' and '.join(shows)}, productions similar to this one, also listen to this artist")
    lift = fit.inputs.get("lift")
    if lift is not None and lift > 0:
        facts.append("this production's audience likes this artist more than audiences of similar productions do")
    audience = fit.inputs.get("audience")
    if audience is not None and audience >= 0.75:
        facts.append("the artist's listeners are a similar age and gender to the production's audience")
    return f"- {{{{{alias}}}}} {match.candidate.name}: " + "; ".join(facts)


def build_brief_prompt(production_id: str, production_name: str, production_type: str, picks: list[tuple[Match, FitScore]], brief: str = "") -> tuple[str, dict[str, str], dict[str, str]]:
    aliases = {"P-1": production_id}
    alias_names = {"P-1": production_name}
    show_aliases: dict[str, str] = {}
    for _, fit in picks:
        for name in fit.inputs.get("fans_also_watch") or []:
            show_aliases.setdefault(name, f"S-{len(show_aliases) + 1}")
    alias_names.update({alias: name for name, alias in show_aliases.items()})
    lines = []
    for index, (match, fit) in enumerate(picks, start=1):
        alias = f"A-{index}"
        aliases[alias] = match.candidate.id
        alias_names[alias] = match.candidate.name
        lines.append(_artist_line(alias, match, fit, show_aliases))
    user = (
        f"<production>\n{{{{P-1}}}} {production_name} ({TYPE_LABELS.get(production_type, 'production')})\n</production>\n"
        f"<brief>\n{brief or '(none)'}\n</brief>\n"
        f"<artists>\n" + "\n".join(lines) + "\n</artists>\nWrite one reason per artist."
    )
    return user, aliases, alias_names


@dataclass(frozen=True)
class BriefOutcome:
    items: tuple[BriefItem, ...]
    drops: tuple[Drop, ...]


async def write_brief(
    production_id: str,
    production_name: str,
    production_type: str,
    picks: list[tuple[Match, FitScore]],
    llm: LLMCall = structured,
    brief: str = "",
) -> BriefOutcome:
    if not picks:
        return BriefOutcome((), ())
    user, aliases, alias_names = build_brief_prompt(production_id, production_name, production_type, picks, brief)
    artist_aliases = [a for a in aliases if a.startswith("A-")]
    try:
        raw = await _call(
            llm,
            label="writer_brief",
            system=instructions.BRIEF_SYSTEM,
            user=user,
            schema=instructions.brief_schema(artist_aliases),
            prompt_version=instructions.BRIEF_PROMPT_VERSION,
            max_tokens=8000,
        )
    except LLMError as failure:
        return BriefOutcome((), (Drop("writer", f"no reasons written: {failure}", ""),))
    by_alias = {f"A-{i}": pair for i, pair in enumerate(picks, start=1)}
    drafts: list[BriefItem] = []
    drops: list[Drop] = []
    seen: set[str] = set()
    for entry in raw.get("items") or []:
        alias = entry.get("candidate_id")
        if alias not in by_alias or alias in seen:
            drops.append(Drop("writer", f"unusable or repeated placeholder {alias}", str(alias)))
            continue
        seen.add(alias)
        match, fit = by_alias[alias]
        drafts.append(BriefItem(candidate=replace(match.candidate, id=alias), fit=fit, reason=str(entry.get("reason") or "")))
    kept, guard_drops = guard_brief_items(drafts, Known(dict(alias_names)))
    real: list[BriefItem] = []
    for item in kept:
        reason, newness = strip_newness_claims(item.reason)
        reason, sound = strip_sound_claims(reason, [*item.fit.inputs.get("genres", ()), *item.fit.inputs.get("styles", ())])
        guard_drops += newness + sound
        reason = reason or brief_fallback(item.candidate.name, item.fit)
        real.append(replace(item, candidate=replace(item.candidate, id=aliases[item.candidate.id]), reason=reason))
    return BriefOutcome(tuple(real), tuple(drops + guard_drops))
