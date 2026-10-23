from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from cue.guards import Drop, Known, guard_pitch_items
from cue.records import PitchItem


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
    real = [replace(item, candidate=replace(item.candidate, id=aliases[item.candidate.id])) for item in kept]
    return real, drops + guard_drops
