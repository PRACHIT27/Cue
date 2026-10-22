from __future__ import annotations

from typing import Any, Mapping

from cue.qloo.errors import ParamRejected

INSIGHTS = "/v2/insights"
SEARCH = "/search"
ENTITIES = "/entities"
TAGS = "/v2/tags"
TAG_TYPES = "/v2/tags/types"
AUDIENCES = "/v2/audiences"
AUDIENCE_TYPES = "/v2/audiences/types"
COMPARE = "/v2/analysis/compare"
TRENDING = "/v2/trending"

ENTITY = "urn:entity:"

FILTER_TYPE_HINTS = {
    "urn:entity:video_game": "use urn:entity:videogame",
    "urn:entity:music": "use urn:entity:artist",
    "urn:entity:food_and_drink": "use urn:entity:place or urn:entity:brand",
}

_SIGNALS = {
    "signal.demographics.age",
    "signal.demographics.audiences",
    "signal.demographics.audiences.weight",
    "signal.demographics.gender",
    "signal.interests.entities",
    "signal.interests.tags",
}

_EVERY_INSIGHTS_TYPE = {
    "filter.type",
    "feature.explainability",
    "take",
    "page",
    "offset",
    "signal.location",
    "signal.location.query",
    "signal.location.radius",
    "operator.signal.interests.tags",
}

_ENTITY_COMMON = _SIGNALS | {
    "bias.trends",
    "filter.exclude.entities",
    "filter.exclude.tags",
    "operator.exclude.tags",
    "filter.external.exists",
    "operator.filter.external.exists",
    "filter.parents.types",
    "filter.popularity.min",
    "filter.popularity.max",
    "filter.results.entities",
    "filter.results.entities.query",
    "filter.tags",
    "operator.filter.tags",
}

_GEO = {
    "filter.geocode.name",
    "filter.geocode.admin1_region",
    "filter.geocode.admin2_region",
    "filter.geocode.country_code",
    "filter.location",
    "filter.location.query",
    "filter.location.radius",
    "filter.location.geohash",
    "filter.exclude.location.geohash",
}

_SCREEN = {
    "filter.content_rating",
    "filter.release_year.min",
    "filter.release_year.max",
    "filter.release_country",
    "operator.filter.release_country",
    "filter.rating.min",
    "filter.rating.max",
}

INSIGHTS_PARAMS: dict[str, frozenset[str]] = {
    ENTITY + "artist": frozenset(_ENTITY_COMMON),
    ENTITY + "book": frozenset(_ENTITY_COMMON | {"filter.publication_year.min", "filter.publication_year.max"}),
    ENTITY + "brand": frozenset(_ENTITY_COMMON),
    ENTITY + "destination": frozenset(_ENTITY_COMMON | _GEO),
    ENTITY + "movie": frozenset(_ENTITY_COMMON | _SCREEN),
    ENTITY + "person": frozenset(
        _ENTITY_COMMON
        | {
            "filter.date_of_birth.min",
            "filter.date_of_birth.max",
            "filter.date_of_death.min",
            "filter.date_of_death.max",
            "filter.gender",
        }
    ),
    ENTITY + "place": frozenset(
        _ENTITY_COMMON
        | _GEO
        | {
            "bias.quality",
            "filter.address",
            "filter.external.tripadvisor.rating.count.max",
            "filter.external.tripadvisor.rating.count.min",
            "filter.external.tripadvisor.rating.max",
            "filter.external.tripadvisor.rating.min",
            "filter.hotel_class.max",
            "filter.hotel_class.min",
            "filter.hours",
            "filter.price_level.min",
            "filter.price_level.max",
            "filter.price_range.from",
            "filter.price_range.to",
            "filter.properties.business_rating.min",
            "filter.properties.business_rating.max",
            "filter.properties.resy.rating.min",
            "filter.properties.resy.rating.max",
            "filter.references_brand",
            "filter.resy.rating_count.min",
            "filter.resy.rating_count.max",
            "filter.resy.rating.party.min",
            "filter.resy.rating.party.max",
            "sort_by",
        }
    ),
    ENTITY + "podcast": frozenset(_ENTITY_COMMON),
    ENTITY + "tv_show": frozenset(
        _ENTITY_COMMON
        | _SCREEN
        | {
            "filter.finale_year.min",
            "filter.finale_year.max",
            "filter.latest_known_year.min",
            "filter.latest_known_year.max",
        }
    ),
    ENTITY + "videogame": frozenset(_ENTITY_COMMON),
    "urn:heatmap": frozenset(
        _SIGNALS
        | {
            "filter.location",
            "filter.location.query",
            "filter.location.radius",
            "heatmap.dimensions",
            "filter.dimensions.hotel_class",
            "filter.dimensions.price_level",
            "output.heatmap.boundary",
        }
    ),
    "urn:tag": frozenset(_SIGNALS | {"diversify.by", "diversify.take", "filter.tag.types", "filter.parents.types"}),
    "urn:demographics": frozenset(_SIGNALS),
}

INSIGHTS_REQUIRED: dict[str, frozenset[str]] = {
    ENTITY + "destination": frozenset({"signal.interests.entities"}),
}

ENDPOINT_PARAMS: dict[str, frozenset[str]] = {
    SEARCH: frozenset(
        {
            "query",
            "types",
            "filter.location",
            "filter.radius",
            "filter.exists",
            "filter.tags",
            "filter.rating",
            "filter.popularity",
            "filter.address",
            "operator.filter.tags",
            "page",
            "take",
            "sort_by",
        }
    ),
    ENTITIES: frozenset(
        {"entity_ids"}
        | {
            f"external.{source}.ids"
            for source in (
                "facebook",
                "goodreads",
                "goodreads_author",
                "igdb",
                "imdb",
                "instagram",
                "isbn10",
                "isbn13",
                "itunes",
                "lastfm",
                "library_of_congress",
                "metacritic",
                "michelin",
                "musicbrainz",
                "rottentomatoes",
                "soundcloud",
                "spotify",
                "tablet",
                "twitch",
                "twitter",
                "wikidata",
                "resy",
            )
        }
    ),
    TAGS: frozenset(
        {
            "feature.typo_tolerance",
            "feature.semantic_search",
            "filter.results.tags",
            "filter.parents.types",
            "filter.popularity.min",
            "filter.popularity.max",
            "filter.query",
            "filter.tag.types",
            "page",
            "take",
        }
    ),
    TAG_TYPES: frozenset({"filter.parents.types", "page", "take"}),
    AUDIENCES: frozenset(
        {
            "filter.parents.types",
            "filter.results.audiences",
            "filter.audience.types",
            "filter.query",
            "filter.popularity.min",
            "filter.popularity.max",
            "page",
            "take",
        }
    ),
    AUDIENCE_TYPES: frozenset({"filter.parents.types", "page", "take"}),
    COMPARE: frozenset(
        {
            "a.signal.interests.entities",
            "b.signal.interests.entities",
            "filter.type",
            "filter.entities.query",
            "filter.exclude.entities.query",
            "filter.location.query",
            "filter.location.radius",
            "filter.exclude.location.query",
            "filter.exclude.location.radius",
            "filter.subtype",
            "model",
            "page",
            "take",
            "offset",
        }
    ),
    TRENDING: frozenset(
        {
            "signal.interests.entities",
            "filter.type",
            "filter.start_date",
            "filter.end_date",
            "take",
            "offset",
            "page",
        }
    ),
}

ENDPOINT_REQUIRED: dict[str, frozenset[str]] = {
    SEARCH: frozenset({"query"}),
    COMPARE: frozenset({"a.signal.interests.entities", "b.signal.interests.entities"}),
    TRENDING: frozenset({"signal.interests.entities", "filter.start_date", "filter.end_date"}),
}


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_value(item) for item in value)
    return str(value)


def normalize(params: Mapping[str, Any]) -> dict[str, str]:
    return {key: _value(value) for key, value in params.items() if value is not None}


def _missing(required: frozenset[str], params: Mapping[str, str]) -> list[str]:
    return [f"missing required parameter {name}" for name in sorted(required) if not params.get(name)]


def _unsupported(allowed: frozenset[str], params: Mapping[str, str], where: str) -> list[str]:
    return [f"{name} is not supported for {where}" for name in sorted(params) if name not in allowed]


def check(endpoint: str, params: Mapping[str, str]) -> None:
    if endpoint == INSIGHTS:
        reasons = _check_insights(params)
    elif endpoint in ENDPOINT_PARAMS:
        reasons = _unsupported(ENDPOINT_PARAMS[endpoint], params, endpoint)
        reasons += _missing(ENDPOINT_REQUIRED.get(endpoint, frozenset()), params)
        if endpoint == ENTITIES and not params:
            reasons.append("pass entity_ids or an external.<source>.ids parameter")
    else:
        reasons = [f"unknown endpoint {endpoint}"]
    if reasons:
        raise ParamRejected(endpoint, reasons)


def _check_insights(params: Mapping[str, str]) -> list[str]:
    filter_type = params.get("filter.type", "")
    if not filter_type:
        return ["missing required parameter filter.type"]
    if filter_type not in INSIGHTS_PARAMS:
        hint = FILTER_TYPE_HINTS.get(filter_type)
        return [f"filter.type {filter_type} is not supported" + (f"; {hint}" if hint else "")]
    allowed = INSIGHTS_PARAMS[filter_type] | _EVERY_INSIGHTS_TYPE
    reasons = _unsupported(allowed, params, f"filter.type {filter_type}")
    reasons += _missing(INSIGHTS_REQUIRED.get(filter_type, frozenset()), params)
    return reasons
