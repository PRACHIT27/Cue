from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from cue.agents.planner.instructions import MAX_BRIEF_TAGS, PRODUCTION_TYPES, SECTIONS

MAX_TAG_CHARS = 40
MAX_NOTE_CHARS = 200
DEFAULT_TYPES = ("tv_show", "movie", "videogame", "podcast")


@dataclass(frozen=True)
class Decision:
    production_types: tuple[str, ...]
    sections: tuple[str, ...]
    brief_tags: tuple[str, ...] = ()
    use_lift: bool = True
    done: bool = False
    note: str = ""
    fallback: bool = False
    problems: tuple[str, ...] = field(default=())


def default_decision(reason: str) -> Decision:
    return Decision(DEFAULT_TYPES, tuple(SECTIONS), (), True, False, "Searched the usual production types in every section.", True, (reason,))


def _ordered(values: Any, allowed: list[str]) -> tuple[str, ...]:
    seen = []
    for value in values if isinstance(values, list) else []:
        if value in allowed and value not in seen:
            seen.append(value)
    return tuple(seen)


def check_decision(raw: Mapping[str, Any], already_searched: set[tuple[str, str]], first_round: bool) -> Decision:
    problems: list[str] = []
    types = _ordered(raw.get("production_types"), PRODUCTION_TYPES)
    sections = _ordered(raw.get("sections"), SECTIONS)

    tags: list[str] = []
    for value in raw.get("brief_tags") or []:
        tag = " ".join(str(value).split())[:MAX_TAG_CHARS]
        if tag and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)
    if len(tags) > MAX_BRIEF_TAGS:
        problems.append(f"kept the first {MAX_BRIEF_TAGS} brief tags of {len(tags)}")
        tags = tags[:MAX_BRIEF_TAGS]

    note = " ".join(str(raw.get("note") or "").split())[:MAX_NOTE_CHARS]
    done = bool(raw.get("done"))

    if first_round and (not types or not sections):
        return default_decision("the plan named no production types or sections")
    fresh = [(t, s) for t in types for s in sections if (t, s) not in already_searched]
    if not first_round and not fresh:
        done = True

    return Decision(types, sections, tuple(tags), bool(raw.get("use_lift", True)), done, note, False, tuple(problems))
