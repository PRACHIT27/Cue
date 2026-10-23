from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from cue.qloo.params import TRENDING
from cue.tools.context import qloo_get
from cue.tools.parse import results_list
from cue.tools.records import TrendSeries, TrendWeek

DATA_ENDS = date(2026, 7, 31)
WEEKS = 12
FETCH_WEEKS = 16
PERCENTILE_SWING = 0.10


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _week(raw: dict) -> TrendWeek | None:
    try:
        week_start = date.fromisoformat(str(raw.get("date"))[:10])
    except ValueError:
        return None
    return TrendWeek(
        week_start=week_start,
        percentile=_float(raw.get("population_percentile")),
        rank=_int(raw.get("population_rank")),
        rank_velocity=_int(raw.get("population_rank_velocity")),
        velocity_fold_change=_float(raw.get("velocity_fold_change")),
    )


async def trending(entity_id: str, entity_type: str) -> TrendSeries:
    start = DATA_ENDS - timedelta(weeks=FETCH_WEEKS)
    data = await qloo_get(
        TRENDING,
        {
            "filter.type": entity_type,
            "signal.interests.entities": entity_id,
            "filter.start_date": start.isoformat(),
            "filter.end_date": DATA_ENDS.isoformat(),
            "take": FETCH_WEEKS + 4,
        },
    )
    weeks = sorted((w for w in map(_week, results_list(data, "trending")) if w), key=lambda w: w.week_start)
    weeks = weeks[-WEEKS:]
    return TrendSeries(entity_id=entity_id, as_of=weeks[-1].week_start if weeks else None, weeks=tuple(weeks))


def trend_score(series: TrendSeries) -> float | None:
    if len(series.weeks) < 2:
        return None
    change = series.weeks[-1].percentile - series.weeks[0].percentile
    return round(max(0.0, min(1.0, 0.5 + change / (2 * PERCENTILE_SWING))), 4)
