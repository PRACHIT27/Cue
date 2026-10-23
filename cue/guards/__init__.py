from __future__ import annotations

from dataclasses import replace

from cue.guards.claims import strip_placement_claims
from cue.guards.grounding import Drop, Known, ground_text
from cue.records import BriefItem, PitchItem


def clean_text(text: str, known: Known, artist_name: str | None = None) -> tuple[str, list[Drop]]:
    grounded, drops = ground_text(text, known, artist_name)
    cleaned, claim_drops = strip_placement_claims(grounded)
    return cleaned, drops + claim_drops


def guard_pitch_items(items: list[PitchItem], known: Known, artist_name: str | None = None) -> tuple[list[PitchItem], list[Drop]]:
    kept: list[PitchItem] = []
    drops: list[Drop] = []
    for item in items:
        if not known.has_id(item.candidate.id):
            drops.append(Drop("grounding", f"candidate {item.candidate.id} was not returned by Qloo", item.candidate.name))
            continue
        reason, d1 = clean_text(item.reason, known, artist_name)
        subject, d2 = clean_text(item.email_subject, known, artist_name)
        body, d3 = clean_text(item.email_body, known, artist_name)
        drops += d1 + d2 + d3
        if not body:
            drops.append(Drop("grounding", "nothing safe left in the email", item.candidate.name))
            continue
        kept.append(replace(item, candidate=replace(item.candidate, name=known.names_by_id[item.candidate.id]), reason=reason, email_subject=subject, email_body=body))
    return kept, drops


def guard_brief_items(items: list[BriefItem], known: Known) -> tuple[list[BriefItem], list[Drop]]:
    kept: list[BriefItem] = []
    drops: list[Drop] = []
    for item in items:
        if not known.has_id(item.candidate.id):
            drops.append(Drop("grounding", f"candidate {item.candidate.id} was not returned by Qloo", item.candidate.name))
            continue
        reason, extra = clean_text(item.reason, known)
        drops += extra
        kept.append(replace(item, candidate=replace(item.candidate, name=known.names_by_id[item.candidate.id]), reason=reason))
    return kept, drops


__all__ = ["Drop", "Known", "clean_text", "guard_brief_items", "guard_pitch_items", "ground_text", "strip_placement_claims"]
