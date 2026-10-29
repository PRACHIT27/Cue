from __future__ import annotations

from typing import Mapping

from cue.records import FitScore, Match
from cue.scoring.sections import section_of

LIFT_WEIGHT = 0.70
AUDIENCE_WEIGHT = 0.30


def score_match(lift_rank: float | None, audience: float | None) -> float | None:
    if lift_rank is None:
        return None
    if audience is None:
        return lift_rank
    return LIFT_WEIGHT * lift_rank + AUDIENCE_WEIGHT * audience


def lift_ranks(lifts: Mapping[str, float]) -> dict[str, float]:
    distinct = sorted(set(lifts.values()), reverse=True)
    if len(distinct) <= 1:
        return {key: 1.0 for key in lifts}
    position = {value: index for index, value in enumerate(distinct)}
    last = len(distinct) - 1
    return {key: round(1 - position[value] / last, 6) for key, value in lifts.items()}


def match_basis(lift: float | None, audience: float | None) -> str:
    if lift is not None and lift > 0:
        return "taste"
    return "audience_only" if audience is not None else "weak"


def score_matches(matches: list[Match], lifts: Mapping[str, float | None]) -> list[FitScore]:
    by_section: dict[str, list[Match]] = {}
    for match in matches:
        by_section.setdefault(section_of(match.candidate.popularity), []).append(match)

    scores: list[FitScore] = []
    for section, members in by_section.items():
        known = {m.candidate.id: lifts[m.candidate.id] for m in members if lifts.get(m.candidate.id) is not None}
        ranks = lift_ranks(known)
        for match in members:
            lift = lifts.get(match.candidate.id)
            rank = ranks.get(match.candidate.id)
            value = score_match(rank, match.audience)
            inputs = {
                "section": section,
                "lift": lift,
                "lift_rank": rank,
                "audience": match.audience,
                "affinity": match.affinity,
                "popularity": match.candidate.popularity,
                "basis": match_basis(lift, match.audience),
            }
            status = "ok" if value is not None else "insufficient_data"
            scores.append(FitScore(match.match_id, value, status, inputs))
    return scores
