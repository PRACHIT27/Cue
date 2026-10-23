from __future__ import annotations

from cue.tools.records import Demographics, InsightsResult


def lift_scores(own: InsightsResult, group: InsightsResult) -> dict[str, float | None]:
    group_affinity = {item.candidate.id: item.affinity for item in group.items}
    for item in group.items:
        for duplicate in item.duplicate_ids:
            group_affinity.setdefault(duplicate, item.affinity)
    if not group_affinity:
        return {item.candidate.id: None for item in own.items}
    floor = min(group_affinity.values())
    lifts: dict[str, float | None] = {}
    for item in own.items:
        ids = (item.candidate.id, *item.duplicate_ids)
        baseline = next((group_affinity[i] for i in ids if i in group_affinity), floor)
        lifts[item.candidate.id] = round(item.affinity - baseline, 6)
    return lifts


def audience_similarity(a: Demographics | None, b: Demographics | None) -> float | None:
    if a is None or b is None:
        return None
    gaps = [abs(a.age[k] - b.age[k]) for k in a.age.keys() & b.age.keys()]
    gaps += [abs(a.gender[k] - b.gender[k]) for k in a.gender.keys() & b.gender.keys()]
    if not gaps:
        return None
    return round(max(0.0, 1 - (sum(gaps) / len(gaps)) / 2), 6)
