from __future__ import annotations

import re
from typing import Iterable

from cue.guards.grounding import Drop
from cue.guards.text import join_sentences, sentences

PLACEMENT_CLAIMS = [
    r"\b(was|were|has been|have been|got|been)\s+(featured|used|placed|played|synced|licensed|included)\b",
    r"\b(song|track|music|single|songs|tracks)\s+(appeared|featured|played)\s+(in|on)\b",
    r"\bsoundtracked\b",
    r"\b(my|our|the|this) (song|track|music|single) (is|was) (in|on)\b",
    r"\blicensed (to|by|for)\b",
    r"\b(previous|past|earlier|recent) (placement|placements|sync|syncs)\b",
    r"\bas heard (in|on)\b",
]
CLAIM = re.compile("|".join(PLACEMENT_CLAIMS), re.IGNORECASE)


def strip_placement_claims(text: str) -> tuple[str, list[Drop]]:
    drops: list[Drop] = []
    kept: list[str] = []
    for sentence in sentences(text):
        if sentence != "\n" and CLAIM.search(sentence):
            drops.append(Drop("claim", "claims a past placement Cue has no data for", sentence))
            continue
        kept.append(sentence)
    return join_sentences(kept), drops


NEWNESS = re.compile(
    r"\b(new|newer|emerging|up[- ]and[- ]coming|rising|breakout|budding|fresh|young)\s+(artist|artists|talent|voice|voices|star|stars|singer|singers|act|acts|musician|musicians|name|names)\b",
    re.IGNORECASE,
)


def strip_newness_claims(text: str) -> tuple[str, list[Drop]]:
    drops: list[Drop] = []
    kept: list[str] = []
    for sentence in sentences(text):
        if sentence != "\n" and NEWNESS.search(sentence):
            drops.append(Drop("claim", "calls an under-the-radar artist new; Cue has no debut dates", sentence))
            continue
        kept.append(sentence)
    return join_sentences(kept), drops


SOUND = re.compile(
    r"\b(?:their|his|her|its)\s+((?:[\w-]+,?\s+){1,3})(?:songs|song|sound|sounds|music|tracks|track|vocals|voice|style|melodies|production)\b",
    re.IGNORECASE,
)
SOUND_JOINERS = {"and", "or"}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _ungrounded_sound(sentence: str, allowed: set[str]) -> bool:
    return any(_words(m.group(1)) - allowed - SOUND_JOINERS for m in SOUND.finditer(sentence))


def strip_sound_claims(text: str, allowed: Iterable[str] = ()) -> tuple[str, list[Drop]]:
    allowed_words = {w for a in allowed for w in _words(a)}
    drops: list[Drop] = []
    kept: list[str] = []
    for sentence in sentences(text):
        if sentence != "\n" and _ungrounded_sound(sentence, allowed_words):
            drops.append(Drop("claim", "describes how an artist sounds with words Qloo never used for them", sentence))
            continue
        kept.append(sentence)
    return join_sentences(kept), drops
