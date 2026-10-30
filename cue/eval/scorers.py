from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

TOP_K = 10


def normalise(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
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
    emerging: int
    seconds: float
    usd: float
    error: str | None = None


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
) -> RowScore:
    top = list(suggestions[:TOP_K])
    found = [r for r in resolved if r.found]
    emerging = sum(1 for r in found if r.popularity is not None and r.popularity <= cap) if mode == "supervisor" else 0
    return RowScore(
        id=record_id,
        system=system,
        mode=mode,
        hit=is_hit(answer, top),
        suggested=len(top),
        made_up=len(resolved) - len(found),
        resolved=len(found),
        emerging=emerging,
        seconds=round(seconds, 2),
        usd=round(usd, 6),
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
            "emerging_share": _rate(sum(r.emerging for r in supervisor), sum(r.resolved for r in supervisor)),
            "median_seconds": round(statistics.median(times), 2) if times else None,
            "slowest_seconds": round(max(times), 2) if times else None,
            "total_usd": round(sum(r.usd for r in items), 4),
        }
    return summary


def row_dict(row: RowScore) -> dict[str, Any]:
    return asdict(row)
