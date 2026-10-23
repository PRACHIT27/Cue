from __future__ import annotations

import re

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
