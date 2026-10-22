from __future__ import annotations

from typing import Any, Mapping

from cue.qloo.params import AUDIENCE_TYPES, AUDIENCES, TAG_TYPES, TAGS
from cue.tools.context import qloo_get
from cue.tools.parse import results_list, tag_ref
from cue.tools.records import AudienceRef, TagRef

TAKE = 20


def _types(items: list[Mapping[str, Any]]) -> list[str]:
    return list(dict.fromkeys(str(item["type"]) for item in items if item.get("type")))


async def find_tags(query: str, tag_types: list[str] | None = None) -> list[TagRef]:
    if not query.strip():
        return []
    params: dict[str, Any] = {"filter.query": query, "take": TAKE}
    if tag_types:
        params["filter.tag.types"] = tag_types
    data = await qloo_get(TAGS, params)
    refs = []
    for raw in results_list(data, "tags"):
        try:
            refs.append(tag_ref(raw))
        except ValueError:
            continue
    return refs


async def get_tag_types() -> list[str]:
    return _types(results_list(await qloo_get(TAG_TYPES, {}), "tag_types"))


async def find_audiences(query: str | None = None, audience_types: list[str] | None = None) -> list[AudienceRef]:
    params: dict[str, Any] = {"take": TAKE}
    if query and query.strip():
        params["filter.query"] = query
    if audience_types:
        params["filter.audience.types"] = audience_types
    data = await qloo_get(AUDIENCES, params)
    refs = []
    for raw in results_list(data, "audiences"):
        audience_id = raw.get("id") or raw.get("entity_id")
        if audience_id:
            refs.append(AudienceRef(id=str(audience_id), name=str(raw.get("name") or ""), type=str(raw.get("type") or "")))
    return refs


async def get_audience_types() -> list[str]:
    return _types(results_list(await qloo_get(AUDIENCE_TYPES, {}), "audience_types"))
