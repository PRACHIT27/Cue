from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

TOP_K = 10


def normalise(name: str) -> str:
    text = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[4:] if text.startswith("the ") else text


def is_hit(answer: str | None, suggestions: Sequence[str], k: int = TOP_K) -> bool | None:
    if not answer:
        return None
    wanted = normalise(answer)
    return any(normalise(s) == wanted for s in suggestions[:k])


@dataclass(frozen=True)
class Resolved:
    name: str
    found: bool
    popularity: float | None


@dataclass(frozen=True)
class RowScore:
    id: str
    system: str
    mode: str
    hit: bool | None
    suggested: int
    made_up: int
    resolved: int
    under_radar: int
    seconds: float
    usd: float
    error: str | None = None
    answer_above_cap: bool = False
    mean_popularity: float | None = None


def score_row(
    record_id: str,
    system: str,
    mode: str,
    answer: str | None,
    suggestions: Sequence[str],
    resolved: Sequence[Resolved],
    cap: float,
    seconds: float,
    usd: float,
    answer_popularity: float | None = None,
) -> RowScore:
    top = list(suggestions[:TOP_K])
    found = [r for r in resolved if r.found]
    under_radar = sum(1 for r in found if r.popularity is not None and r.popularity <= cap) if mode == "supervisor" else 0
    above_cap = mode == "supervisor" and answer_popularity is not None and answer_popularity > cap
    return RowScore(
        id=record_id,
        system=system,
        mode=mode,
        hit=None if above_cap else is_hit(answer, top),
        suggested=len(top),
        made_up=len(resolved) - len(found),
        resolved=len(found),
        under_radar=under_radar,
        seconds=round(seconds, 2),
        usd=round(usd, 6),
        answer_above_cap=above_cap,
        mean_popularity=round(statistics.mean(r.popularity for r in found if r.popularity is not None), 4) if any(r.popularity is not None for r in found) else None,
    )


def failed_row(record_id: str, system: str, mode: str, error: str, seconds: float, usd: float) -> RowScore:
    return RowScore(record_id, system, mode, None, 0, 0, 0, 0, round(seconds, 2), round(usd, 6), error)


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def summarise(rows: Iterable[RowScore]) -> dict[str, Any]:
    by_system: dict[str, list[RowScore]] = {}
    for row in rows:
        by_system.setdefault(row.system, []).append(row)
    summary: dict[str, Any] = {}
    for system, items in by_system.items():
        ok = [r for r in items if r.error is None]
        judged = [r for r in ok if r.hit is not None]
        supervisor = [r for r in ok if r.mode == "supervisor"]
        times = [r.seconds for r in ok]
        summary[system] = {
            "rows": len(items),
            "errors": len(items) - len(ok),
            "hit_rate_top10": _rate(sum(1 for r in judged if r.hit), len(judged)),
            "hit_rows": len(judged),
            "made_up_rate": _rate(sum(r.made_up for r in ok), sum(r.made_up + r.resolved for r in ok)),
            "names_checked": sum(r.made_up + r.resolved for r in ok),
            "under_the_radar_share": _rate(sum(r.under_radar for r in supervisor), sum(r.resolved for r in supervisor)),
            "answers_above_cap": sum(1 for r in ok if r.answer_above_cap),
            "median_suggestion_popularity": round(statistics.median(p), 4) if (p := [r.mean_popularity for r in ok if r.mean_popularity is not None]) else None,
            "median_seconds": round(statistics.median(times), 2) if times else None,
            "slowest_seconds": round(max(times), 2) if times else None,
            "total_usd": round(sum(r.usd for r in items), 4),
        }
    return summary


def row_dict(row: RowScore) -> dict[str, Any]:
    return asdict(row)


def repeat_share(suggestions_by_row: Iterable[Sequence[str]], min_rows: int = 3) -> float | None:
    lists = [list(dict.fromkeys(normalise(n) for n in names)) for names in suggestions_by_row]
    total = sum(len(names) for names in lists)
    if not total:
        return None
    counts: dict[str, int] = {}
    for names in lists:
        for name in names:
            counts[name] = counts.get(name, 0) + 1
    repeated = sum(1 for names in lists for name in names if counts[name] >= min_rows)
    return round(repeated / total, 4)
