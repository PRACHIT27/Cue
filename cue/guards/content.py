from __future__ import annotations

import re
from typing import Iterable

from cue.guards.grounding import Drop
from cue.tools.records import InsightsItem

EXPLICIT_WORDS = [
    "porn",
    "porno",
    "xxx",
    "nsfw",
    "erotic",
    "erotica",
    "sex",
    "sexy",
    "hentai",
    "fetish",
    "onlyfans",
    "nude",
    "naked",
    "strip club",
    "escort",
]
EXPLICIT = re.compile(r"\b(" + "|".join(re.escape(w) for w in EXPLICIT_WORDS) + r")\b", re.IGNORECASE)


def is_explicit(name: str) -> bool:
    return bool(EXPLICIT.search(name))


def remove_explicit(items: Iterable[InsightsItem]) -> tuple[list[InsightsItem], list[Drop]]:
    kept: list[InsightsItem] = []
    drops: list[Drop] = []
    for item in items:
        if is_explicit(item.candidate.name):
            drops.append(Drop("content", "explicit title", item.candidate.name))
            continue
        kept.append(item)
    return kept, drops
