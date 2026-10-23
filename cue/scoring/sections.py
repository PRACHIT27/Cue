from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    name: str
    popularity_min: float | None
    popularity_max: float | None


SECTIONS = (
    Section("big_screen", 0.90, None),
    Section("prime_time", 0.70, 0.90),
    Section("indie_gems", None, 0.70),
)


def section_of(popularity: float) -> str:
    for section in SECTIONS:
        above = section.popularity_min is None or popularity >= section.popularity_min
        below = section.popularity_max is None or popularity < section.popularity_max
        if above and below:
            return section.name
    return SECTIONS[-1].name
