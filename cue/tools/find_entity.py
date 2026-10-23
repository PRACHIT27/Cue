from __future__ import annotations

from typing import Any, Mapping

from cue.qloo.params import SEARCH
from cue.tools.context import qloo_get
from cue.tools.names import names_match
from cue.tools.parse import akas, entity_ref, external_id, results_list
from cue.tools.records import EntityRef

SEARCH_TAKE = 10
ARTIST = "urn:entity:artist"
PERSON = "urn:entity:person"


def _search_types(types: list[str]) -> list[str]:
    if ARTIST in types:
        return [t for t in types if t != PERSON]
    return list(types)


def _is_exact(name: str, raw: Mapping[str, Any]) -> bool:
    return any(names_match(name, candidate) for candidate in [str(raw.get("name") or ""), *akas(raw)])


def _identity(raw: Mapping[str, Any]) -> tuple[str, ...]:
    keys = []
    for source in ("spotify", "musicbrainz"):
        value = external_id(raw, source)
        if value:
            keys.append(f"{source}:{value}")
    return tuple(keys)


def _merge_same_artist(hits: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    kept: list[Mapping[str, Any]] = []
    seen: dict[str, int] = {}
    for raw in sorted(hits, key=lambda r: -float(r.get("popularity") or 0)):
        index = next((seen[key] for key in _identity(raw) if key in seen), None)
        if index is None:
            index = len(kept)
            kept.append(raw)
        for key in _identity(raw):
            seen.setdefault(key, index)
    return kept


async def find_entity(name: str, types: list[str]) -> list[EntityRef]:
    if not name.strip():
        return []
    search_types = _search_types(types)
    data = await qloo_get(SEARCH, {"query": name, "types": search_types, "take": SEARCH_TAKE})
    hits = [raw for raw in results_list(data) if raw.get("entity_id") and _is_exact(name, raw)]
    if search_types:
        hits = [raw for raw in hits if set(raw.get("types") or []) & set(search_types)]
    return [entity_ref(raw) for raw in _merge_same_artist(hits)]
