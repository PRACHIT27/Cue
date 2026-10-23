from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from cue.guards import Drop, Known, guard_pitch_items
from cue.records import FitScore, PitchItem


def check_pitches(
    drafts: list[PitchItem],
    aliases: Mapping[str, str],
    alias_names: Mapping[str, str],
    artist_name: str,
) -> tuple[list[PitchItem], list[Drop]]:
    seen: set[str] = set()
    unique: list[PitchItem] = []
    drops: list[Drop] = []
    for draft in drafts:
        if draft.candidate.id in seen:
            drops.append(Drop("writer", "second pitch for the same production", draft.candidate.id))
            continue
        seen.add(draft.candidate.id)
        unique.append(draft)
    kept, guard_drops = guard_pitch_items(unique, Known(dict(alias_names)), artist_name)
    real = [
        replace(item, candidate=replace(item.candidate, id=aliases[item.candidate.id]), reason=item.reason or pitch_fallback(item.candidate.name, item.fit))
        for item in kept
    ]
    return real, drops + guard_drops


def pitch_fallback(production_name: str, fit: FitScore) -> str:
    lift = fit.inputs.get("lift")
    if lift is not None and lift > 0:
        return f"People who watch {production_name} like music like yours more than fans of similar artists do."
    audience = fit.inputs.get("audience")
    if audience is not None and audience >= 0.75:
        return f"The audience of {production_name} is a similar age and gender to your listeners."
    return f"Your listeners' tastes overlap with the audience of {production_name}."


def brief_fallback(artist_name: str, fit: FitScore) -> str:
    lift = fit.inputs.get("lift")
    if lift is not None and lift > 0:
        return f"This production's audience likes {artist_name} more than audiences of similar productions do."
    audience = fit.inputs.get("audience")
    if audience is not None and audience >= 0.75:
        return f"{artist_name}'s listeners are a similar age and gender to this production's audience."
    return f"{artist_name}'s listeners share tastes with this production's audience."

