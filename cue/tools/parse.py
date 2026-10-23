from __future__ import annotations

from typing import Any, Mapping

from cue.tools.records import Entity, EntityRef, TagRef


def _clamp(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def entity_type(raw: Mapping[str, Any]) -> str:
    types = raw.get("types") or []
    if types:
        return str(types[0])
    subtype = str(raw.get("subtype") or "")
    if subtype.startswith("urn:entity:"):
        return subtype
    for key in ("type", "subtype"):
        if raw.get(key):
            return str(raw[key])
    raise ValueError(f"Qloo entity {raw.get('entity_id', '?')} has no type")


def entity_ref(raw: Mapping[str, Any]) -> EntityRef:
    entity_id = raw.get("entity_id")
    if not entity_id:
        raise ValueError("Qloo entity has no entity_id")
    return EntityRef(
        id=str(entity_id),
        name=str(raw.get("name") or ""),
        type=entity_type(raw),
        popularity=_clamp(raw.get("popularity")),
    )


def tag_ref(raw: Mapping[str, Any]) -> TagRef:
    tag_id = raw.get("tag_id") or raw.get("id") or raw.get("value")
    if not tag_id:
        raise ValueError("Qloo tag has no id")
    return TagRef(id=str(tag_id), name=str(raw.get("name") or ""), type=str(raw.get("type") or raw.get("subtype") or ""))


def external_id(raw: Mapping[str, Any], source: str) -> str | None:
    external = (raw.get("properties") or {}).get("external") or {}
    value = external.get(source)
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, Mapping):
        value = value.get("id")
    return str(value) if value else None


def _lastfm(raw: Mapping[str, Any], field_name: str) -> int | None:
    lastfm = ((raw.get("properties") or {}).get("external") or {}).get("lastfm") or {}
    if isinstance(lastfm, list):
        lastfm = lastfm[0] if lastfm else {}
    value = lastfm.get(field_name) if isinstance(lastfm, Mapping) else None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def entity(raw: Mapping[str, Any]) -> Entity:
    properties = raw.get("properties") or {}
    image = properties.get("image") or {}
    tags = []
    for tag in raw.get("tags") or []:
        try:
            tags.append(tag_ref(tag))
        except ValueError:
            continue
    return Entity(
        ref=entity_ref(raw),
        description=properties.get("short_description") or properties.get("description"),
        image_url=image.get("url") if isinstance(image, Mapping) else None,
        spotify_id=external_id(raw, "spotify"),
        musicbrainz_id=external_id(raw, "musicbrainz"),
        wikidata_id=external_id(raw, "wikidata"),
        lastfm_listeners=_lastfm(raw, "listeners"),
        lastfm_scrobbles=_lastfm(raw, "scrobbles"),
        tags=tuple(tags),
    )


def akas(raw: Mapping[str, Any]) -> list[str]:
    values = (raw.get("properties") or {}).get("akas") or []
    names = []
    for value in values:
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, Mapping) and value.get("value"):
            names.append(str(value["value"]))
    return names


def results_list(data: Any, key: str | None = None) -> list[Mapping[str, Any]]:
    if not isinstance(data, Mapping):
        return []
    results = data.get("results")
    if isinstance(results, list):
        return results
    if isinstance(results, Mapping) and key:
        value = results.get(key)
        return value if isinstance(value, list) else []
    return []
