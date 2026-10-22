from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class EntityRef:
    id: str
    name: str
    type: str
    popularity: float


@dataclass(frozen=True)
class TagRef:
    id: str
    name: str
    type: str


@dataclass(frozen=True)
class AudienceRef:
    id: str
    name: str
    type: str


@dataclass(frozen=True)
class Entity:
    ref: EntityRef
    description: str | None = None
    image_url: str | None = None
    spotify_id: str | None = None
    musicbrainz_id: str | None = None
    wikidata_id: str | None = None
    lastfm_listeners: int | None = None
    lastfm_scrobbles: int | None = None
    tags: tuple[TagRef, ...] = ()


@dataclass(frozen=True)
class InsightsRequest:
    filter_type: str
    signal_entities: tuple[str, ...] = ()
    signal_tags: tuple[str, ...] = ()
    popularity_min: float | None = None
    popularity_max: float | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    take: int = 20


@dataclass(frozen=True)
class InsightsItem:
    candidate: EntityRef
    affinity: float
    rank: int
    explanation: dict[str, float]
    duplicate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Demographics:
    entity_id: str
    age: dict[str, float]
    gender: dict[str, float]


@dataclass(frozen=True)
class HeatPoint:
    latitude: float
    longitude: float
    geohash: str
    affinity: float
    popularity: float


@dataclass(frozen=True)
class InsightsResult:
    request: InsightsRequest
    items: tuple[InsightsItem, ...] = ()
    tags: tuple[tuple[TagRef, float], ...] = ()
    demographics: tuple[Demographics, ...] = ()
    heatmap: tuple[HeatPoint, ...] = ()


@dataclass(frozen=True)
class CompareResult:
    a_ids: tuple[str, ...]
    b_ids: tuple[str, ...]
    shared: tuple[tuple[TagRef, float], ...]
    a_tags: tuple[TagRef, ...]
    b_tags: tuple[TagRef, ...]


@dataclass(frozen=True)
class TrendWeek:
    week_start: date
    percentile: float
    rank: int
    rank_velocity: int
    velocity_fold_change: float


@dataclass(frozen=True)
class TrendSeries:
    entity_id: str
    as_of: date | None
    weeks: tuple[TrendWeek, ...]
