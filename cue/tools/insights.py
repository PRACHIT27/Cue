from __future__ import annotations

from typing import Any, Mapping

from cue.qloo.params import INSIGHTS
from cue.tools.context import qloo_get
from cue.tools.names import normalise_name
from cue.tools.parse import entity_ref, results_list, tag_ref
from cue.tools.records import Demographics, HeatPoint, InsightsItem, InsightsRequest, InsightsResult

DEMOGRAPHICS = "urn:demographics"
HEATMAP = "urn:heatmap"
TAG = "urn:tag"
DEFAULT_POPULARITY_MAX = {"urn:entity:videogame": 0.90}


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _params(request: InsightsRequest) -> dict[str, Any]:
    params: dict[str, Any] = {"filter.type": request.filter_type, **request.filters}
    if request.signal_entities:
        params["signal.interests.entities"] = list(request.signal_entities)
    if request.signal_tags:
        params["signal.interests.tags"] = list(request.signal_tags)
    if request.filter_type.startswith("urn:entity:"):
        params["feature.explainability"] = True
        params["take"] = request.take
        popularity_max = request.popularity_max
        if popularity_max is None and request.popularity_min is None:
            popularity_max = DEFAULT_POPULARITY_MAX.get(request.filter_type)
        if request.popularity_min is not None:
            params["filter.popularity.min"] = request.popularity_min
        if popularity_max is not None:
            params["filter.popularity.max"] = popularity_max
    return params


def _explanation(raw: Mapping[str, Any]) -> dict[str, float]:
    explain = (raw.get("query") or {}).get("explainability") or {}
    shares = explain.get("signal.interests.entities") or []
    return {str(s["entity_id"]): round(_number(s.get("score")), 4) for s in shares if isinstance(s, Mapping) and s.get("entity_id")}


def _items(data: Any) -> tuple[InsightsItem, ...]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    for raw in results_list(data, "entities"):
        try:
            ref = entity_ref(raw)
        except ValueError:
            continue
        affinity = max(0.0, min(1.0, _number((raw.get("query") or {}).get("affinity", raw.get("affinity")))))
        key = (normalise_name(ref.name), ref.type)
        if key not in best:
            order.append(key)
            best[key] = {"ref": ref, "affinity": affinity, "explanation": _explanation(raw), "ids": [ref.id]}
            continue
        entry = best[key]
        entry["ids"].append(ref.id)
        if affinity > entry["affinity"]:
            entry.update(ref=ref, affinity=affinity, explanation=_explanation(raw))
    ranked = sorted(order, key=lambda k: -best[k]["affinity"])
    return tuple(
        InsightsItem(
            candidate=best[k]["ref"],
            affinity=best[k]["affinity"],
            rank=position,
            explanation=best[k]["explanation"],
            duplicate_ids=tuple(i for i in best[k]["ids"] if i != best[k]["ref"].id),
        )
        for position, k in enumerate(ranked, start=1)
    )


def _tags(data: Any) -> tuple:
    found = []
    for raw in results_list(data, "tags"):
        try:
            found.append((tag_ref(raw), _number((raw.get("query") or {}).get("affinity", 0.0))))
        except ValueError:
            continue
    return tuple(found)


def _demographics(data: Any) -> tuple[Demographics, ...]:
    blocks = []
    for raw in results_list(data, "demographics"):
        query = raw.get("query") or {}
        blocks.append(
            Demographics(
                entity_id=str(raw.get("entity_id") or ""),
                age={k: _number(v) for k, v in (query.get("age") or {}).items()},
                gender={k: _number(v) for k, v in (query.get("gender") or {}).items()},
            )
        )
    return tuple(blocks)


def _heatmap(data: Any) -> tuple[HeatPoint, ...]:
    points = []
    for raw in results_list(data, "heatmap"):
        location, query = raw.get("location") or {}, raw.get("query") or {}
        points.append(
            HeatPoint(
                latitude=_number(location.get("latitude")),
                longitude=_number(location.get("longitude")),
                geohash=str(location.get("geohash") or ""),
                affinity=_number(query.get("affinity")),
                popularity=_number(query.get("popularity")),
            )
        )
    return tuple(points)


async def insights(request: InsightsRequest) -> InsightsResult:
    data = await qloo_get(INSIGHTS, _params(request))
    if request.filter_type == DEMOGRAPHICS:
        return InsightsResult(request=request, demographics=_demographics(data))
    if request.filter_type == HEATMAP:
        return InsightsResult(request=request, heatmap=_heatmap(data))
    if request.filter_type == TAG:
        return InsightsResult(request=request, tags=_tags(data))
    return InsightsResult(request=request, items=_items(data))
