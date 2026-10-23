from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from cue.guards.text import fill_placeholders, join_sentences, placeholder_ids, quoted_titles, sentences
from cue.tools.names import normalise_name


@dataclass(frozen=True)
class Drop:
    guard: str
    reason: str
    text: str


@dataclass(frozen=True)
class Known:
    names_by_id: Mapping[str, str]

    @classmethod
    def from_refs(cls, refs: Iterable) -> Known:
        return cls({ref.id: ref.name for ref in refs})

    def has_id(self, entity_id: str) -> bool:
        return entity_id in self.names_by_id

    def has_name(self, name: str) -> bool:
        wanted = normalise_name(name)
        return any(normalise_name(known) == wanted for known in self.names_by_id.values())


def ground_text(text: str, known: Known, artist_name: str | None = None) -> tuple[str, list[Drop]]:
    drops: list[Drop] = []
    kept: list[str] = []
    for sentence in sentences(text):
        if sentence == "\n":
            kept.append(sentence)
            continue
        unknown_ids = [i for i in placeholder_ids(sentence) if not known.has_id(i)]
        if unknown_ids:
            drops.append(Drop("grounding", f"unknown entity id {unknown_ids[0]}", sentence))
            continue
        filled = fill_placeholders(sentence, known.names_by_id)
        allowed_names = [artist_name] if artist_name else []
        unknown_titles = [
            t for t in quoted_titles(filled) if not known.has_name(t) and not any(normalise_name(t) == normalise_name(a) for a in allowed_names)
        ]
        if unknown_titles:
            drops.append(Drop("grounding", f"name not returned by Qloo: {unknown_titles[0]}", filled))
            continue
        kept.append(filled)
    return join_sentences(kept), drops
